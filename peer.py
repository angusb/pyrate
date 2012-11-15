import socket

from bitarray import bitarray

import message
from message import Msg

PORT = 6882
RECV_LEN = 1024*1024

class Peer(object):
    def __init__(self, client, host, port, sock=None):
        self.client = client # reference to client

        self.host = host
        self.port = port
        self.read_buffer = ''
        self.write_buffer = ''
        self.send_queue = []

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

        # The one connecting to a peer is oblidged to handshake immediately
        self.add_message(self.client.handshake())

        # self._send_handshake()

        # # Receive handshake
        # self._receive_handshake()

        def __repr__(self):
            return '<Peer {ip}:{port}>'.format(ip=self.ip, port=self.port)

    def add_message(self, msg):
        """Add a message (str or Msg) to the queue to be sent."""
        self.send_queue.append(msg)
        # if isinstance(msg, str):
        #     self.send_queue.append(msg)
        # elif isinstance(msg, Msg):
        #     self.send_queue.append(msg.bytestring)
        # else:
        #     raise Exception('Can\'t add message of type %s' % type(msg))

    def host_and_port(self):
        """Return a tuple of host and port of the peer"""
        return (self.host, self.port)

    def fileno(self):
        """Gives the illusion that this object is a file descriptor."""
        return self.sock.fileno()

    def read_data(self):
        try:
           data = self.sock.recv(RECV_LEN)
        except socket.error, e:
            # print 'Connection dieing to peer %s because connection refused.' % self.host
            # self.client.reactor.remove_reader(self).
            return

        if not data:
            # print "Connecting dieing because we didn't receive data from %s." % self.host
            # self.client.reactor.remove_reader(self)
            return

        self.read_buffer += data
        msgs, self.read_buffer = self.parse_message(self.read_buffer)

        # TODO: enforce that the first message ever received is a handshake
        #       and isn't received again...?

        for msg in msgs:
            print 'Reading message %s' % msg.kind

            if msg.kind == 'handshake':
                if self.is_good_handshake(msg.info_hash): # TODO: blacklist?
                    m = Msg('handshake',
                            info_hash=self.client.torrent.info_hash,
                            peer_id=self.client.my_peer_id)
                    self.add_message(m)
                    # self.add_message(Msg('unchoke'))
                    self.add_message(Msg('interested'))

            elif msg.kind == 'choke' or msg.kind == 'unchoke':
                self.peer_choking = True if msg.kind == 'choke' else False

            elif msg.kind == 'interested' or msg.kind == 'not_interested':
                self.peer_interested = True if msg.kind == 'interested' else False

            elif msg.kind == "bitfield":
                byte_field = [ord(b) for b in msg.bitfield]
                for byte_idx, byte in enumerate(byte_field):
                    # Most significant bit corresponds to smaller piece index
                    for i in range(8):
                        has_piece = (byte >> i) & 1
                        if has_piece:
                            self.pieces.add(byte_idx * 8 + i)
                print self.pieces

            elif msg.kind == "have":
                print 'has index:', msg.index
                self.pieces.add(msg.index)

            else:
                print 'not yet implemented'

    def write_data(self):
        for s in self.send_queue:
            self.write_buffer += str(s)

        self.send_queue = []

        if self.write_buffer:
            print 'len prior to write', len(self.write_buffer)
            bytes_sent = self.sock.send(self.write_buffer)
            print 'num bytes written', bytes_sent
            self.write_buffer = self.write_buffer[bytes_sent:]

        # else:
        #     self.reactor.remove_writer(self)

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

    def is_good_handshake(self, buff):
        if self.client.torrent.info_hash != buff:
            return False # TODO raise?
        return True
