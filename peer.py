import socket
import logging

import message
from message import Msg

log = logging.getLogger('peer')

RECV_LEN = 1024*1024

class PeerException(Exception):
    pass

class Peer(object):
    def __init__(self, host, port, atorrent=None, client=None, sock=None):
        if not ((not atorrent and (client and sock)) or
                (atorrent and (not client and not sock))):
            raise TypeError('Peer can only be constructed with an ActiveTorrent ' +
                            'or a client and socket')
        self.atorrent = atorrent

        self.host = host
        self.port = port
        self.read_buffer = ''
        self.write_buffer = ''
        self.send_queue = []

        self.handshake = None
        self.pieces = set()

        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False

        if not sock:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
        else:
            self.sock = sock

        self.msg_handler = {
            'handshake': self._handshake,
            'choke': self._choke,
            'unchoke': self._unchoke,
            'interested': self._interested,
            'not_interested': self._not_interested,
            'bitfield': self._have_or_bitfield,
            'have': self._have_or_bitfield,
            'piece': self._piece,
        }

        # If we are connecting, we are oblidged to handshake immediately
        if atorrent:
            self.client = atorrent.client
            self.establish_connection()
        else:
            self.client = client

    def __repr__(self):
        return '<Peer {host}:{port}>'.format(host=self.host, port=self.port)

    def add_message(self, msg):
        """Add a message (str or Msg) to the queue to be sent. If the msg
        is a particular type of message (choke, unchoke, interested,
        not_interested) update the internal state.
        """
        if isinstance(msg, Msg):
            if msg.kind == 'choke':
                self.am_choking = True
            elif msg.kind == 'unchoke':
                self.am_choking = False
            elif msg.kind == 'interested':
                self.am_interested = True
            elif msg.kind == 'not_interested':
                self.am_interested = False

        self.atorrent.client.reactor.reg_writer(self)
        self.send_queue.append(msg)

    def host_and_port(self):
        """Return a tuple of host and port of the peer"""
        return (self.host, self.port)

    def establish_connection(self):
        """Add a handshake and bitfield message to the queue of messages to be
        sent. Requires this peer to be associated with a torrent."""
        assert self.atorrent

        self.add_message(self.atorrent.handshake())

        bitfield = self.atorrent.strategy.get_bitfield()
        self.add_message(Msg('bitfield', bitfield=bitfield))

    def fileno(self):
        """Gives the illusion that this object is a file descriptor."""
        return self.sock.fileno()

    def read_event(self):
        try:
           data = self.sock.recv(RECV_LEN)
        except socket.error, e:
            log.info('Connection dieing to peer %s because connection refused.' % self.host)
            self.client.reactor.remove_reader_writer(self)
            return

        # Connection has been closed
        if not data:
            log.info("Connecting dieing because we didn't receive data from %s." % self.host)
            self.client.reactor.remove_reader_writer(self)
            return

        self.read_buffer += data
        msgs, self.read_buffer = self.parse_message(self.read_buffer)

        for msg in msgs:
            print 'Reading message %s' % msg.kind
            try:
                self.msg_handler[msg.kind](msg)
            except PeerException, p:
                log.info('Dropping peer %s - ' % (repr(self), str(p)))
                self.atorrent.drop_peer(self)
            except KeyError, e:
                log.debug('%s not implemented yet' % e)
                print "'%s' not implemented yet.." % e

    def _handshake(self, msg):
        if self.handshake:
            raise PeerException('Received second handshake')

        self.handshake = msg

        # If there is no associated torrent, set it. This is the last place
        # where we will have to fuss with state relating to the parrent torrent
        if not self.atorrent:
            found_torrent = self.client.add_torrent_peer(self, msg.info_hash)
            if not found_torrent:
                log.info('Removing %s because no related torrent was found.' %
                         repr(Peer))
                self.client.reactor.remove_reader_writer(self)
        else:
            if not self.is_good_handshake(msg.info_hash):
                raise PeerException('Received handshake with bad info hash')

    def _choke(self, msg):
        self.peer_choking = True
        if self.am_interested or self.atorrent.strategy.am_interested(self):
            self.add_message(Msg('interested'))

    def _unchoke(self, msg):
        self.peer_choking = False
        if not self.am_interested:
            log.warning('We are getting unchoked yet we aren\'t interested...')

        if self.am_interested or self.atorrent.strategy.am_interested(self):
            self.prepare_next_request()

    def _interested(self, msg):
        self.peer_interested = True
        if self.am_choking:
            self.add_message(Msg('unchoke')) # TODO

    def _not_interested(self, msg):
        self.peer_interested = False
        if not self.am_choking:
            self.add_message(Msg('choke'))

    def _have_or_bitfield(self, msg):
        if msg.kind == 'bitfield':
            byte_field = [ord(b) for b in msg.bitfield]
            for byte_idx, byte in enumerate(byte_field):
                # Most significant bit corresponds to smaller piece index
                for i in reversed(range(8)):
                    has_piece = (byte >> i) & 1
                    if has_piece:
                        self.pieces.add(byte_idx * 8 + (7-i))
            log.info('peer has pieces ' + str(self.pieces))
        else:
            self.pieces.add(msg.index)

        strat_interested = self.atorrent.strategy.am_interested(self)

        if not self.am_interested and strat_interested:
            self.add_message(Msg('interested'))
            return

        if not self.peer_choking and self.am_interested and strat_interested:
            self.prepare_next_request()

    def _piece(self, msg):
        # TODO: error checking on msg params
        print 'Reading message piece %d' % msg.index
        if self.peer_choking:
            log.error('in an impossible state of being choked yet receiving a msg..?')

        complete = self.atorrent.strategy.add_piece_block(msg.index,
                                                          msg.begin,
                                                          msg.block)
        if complete:
            self.atorrent.broadcast_have(msg.index, exclude=self)
            piece = self.atorrent.pieces[msg.index]
            self.atorrent.file_writer.add_piece(msg.index, piece.data)
            if self.atorrent.strategy.has_all_pieces():
                self.atorrent.finish()
                return

        if self.atorrent.strategy.am_interested(self):
            self.prepare_next_request()

    def prepare_next_request(self):
        """Add the next requests messages to the write queue."""
        for msg in self.atorrent.strategy.get_next_request(self):
            self.add_message(msg)

    def write_data(self):
        print self.send_queue
        for s in self.send_queue:
            self.write_buffer += str(s)

        self.send_queue = []

        if self.write_buffer:
            # print 'len prior to write', len(self.write_buffer)
            bytes_sent = self.sock.send(self.write_buffer)
            # print 'num bytes written', bytes_sent
            self.write_buffer = self.write_buffer[bytes_sent:]
            self.atorrent.client.reactor.unreg_writer(self)
        else:
            log.error("write_data() called for %s with no write_buffer" %
                      repr(self))

    def parse_message(self, buff):
        """Returns a tuple of a list of Msg's and the remaining bytes.
        Note: if a Msg cannot be formed out of buff (i.e. buff isn't large
        enough), ([], buff) is returned.

        Args:
            buff (str)

        Returns:
            tuple ([Msg, ...], str)
        """
        msgs = []
        while True:
            msg, buff = message.parse_message(buff)
            if msg is None:
                break
            msgs.append(msg)

        return msgs, buff

    def is_good_handshake(self, info_hash):
        return self.atorrent.info_hash == info_hash
