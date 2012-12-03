import hashlib
import math
import logging
import socket

import requests
import bencode

from peer import Peer
from message import Msg
from strategy import Strategy
from filewriter import FileManager
from piece import Piece, FinalPiece

from constants import BLOCK_SIZE
log = logging.getLogger('torrent')
PORT = 6882

class TorrentFile(object):
    def __init__(self, file_name, metainfo=None):
        """Constructs a TorrentFile by reading a .torrent file or
        using a info_dict. If metainfo is passsed, file_name is not read.

        Args:
            file_name (str)
        Kwargs:
            info_dict (dict)
        """
        # TODO: Error checking
        if not metainfo:
            with open(file_name, 'r') as f:
                contents = f.read()

        # TODO: make into properties?
        self.metainfo = metainfo if metainfo else bencode.bdecode(contents)
        self.info_dict = self.metainfo['info']
        self.info_hash = hashlib.sha1(bencode.bencode(self.info_dict)).digest()

        log.info('Torrent %s has %d pieces\n' % (file_name, self.num_pieces()))

    def get_length(self):
        # Single File
        if 'length' in self.info_dict:
            return self.info_dict['length']

        # Multi-file format (could be a single file)
        files = self.info_dict['files']
        return sum(f['length'] for f in files)

    def num_pieces(self):
        length = self.info_dict['length']
        return int(math.ceil(float(length) / self.info_dict['piece length']))

    @classmethod
    def create_torrent(cls, 
                       file_name, 
                       tracker_url, 
                       content, 
                       piece_length=512,
                       write=True):
        # TODO: add other options like: announce-list, creation date, comment, created by, encoding
        info_dict = {
            'name': file_name,
            'length': len(contents),
            # Fields common to single and multi-file below
            'piece length': piece_length * 1024,
            'pieces': cls._pieces_hashes(contents)
        }

        metainfo = {
            'info': info_dict,
            'announce': tracker_url
        }

        if write:
            with open(file_name, 'w') as f:
                f.write(bencode.bencode(metainfo))

        return cls(file_name, metainfo)

    @classmethod
    def _pieces_hashes(cls, string, piece_lenth):
        """Return array built from 20-byte SHA1 hashes
            of the string's pieces.
        """
        output = ""
        current_pos = 0
        num_bytes= len(string)
        while current_pos < num_bytes:
            if current_pos + piece_length > num_bytes:
                to_position = num_bytes
            else:
                to_position = current_pos + piece_length

            piece_hash = hashlib.sha1(string[current_pos:to_position]).digest()
            output += piece_hash
            current_pos += piece_length

        return output


class ActiveTorrent(TorrentFile):
    def __init__(self, client, filename, strategy_class=None):
        super(ActiveTorrent, self).__init__(filename)

        self.filename = filename
        self.client = client

        if strategy_class:
            self.strategy = strategy_class(self)

        self.downloaded = 0
        self.uploaded = 0
        self.event = 'started'
        self.tracker_id = None
        self.bytes_left = self.get_length()
        self.peers = []

        self.file_writer = FileManager(self)

        self._init_pieces()

    def _init_pieces(self):
        """Initialize self.pieces to be a list of Pieces"""
        pieces_string = self.info_dict['pieces']
        piece_length = self.info_dict['piece length']

        hashes = [pieces_string[i: i+20] for i in range(0, len(pieces_string), 20)]
        num_pieces = len(hashes)
        num_blocks = piece_length / BLOCK_SIZE

        num_leftover = self.info_dict['length'] - ((num_pieces - 1) * piece_length)
        num_final_blocks = int(math.ceil(float(num_leftover) / BLOCK_SIZE))
        final_size = num_leftover % BLOCK_SIZE

        self.pieces = [Piece(hashes[i], num_blocks) for i in range(num_pieces-1)]
        self.pieces.append(FinalPiece(hashes[-1], num_final_blocks, final_size))

    def broadcast_have(self, piece_index, exclude=None):
        for peer in self.peers:
            if not exclude == peer:
                peer.add_message(Msg('have', index=piece_index))

    def handshake(self):
        pstrlen = chr(19)
        pstr = 'BitTorrent protocol'
        reserved = chr(0) * 8
        h_msg = pstrlen + pstr + reserved + self.info_hash + self.client.peer_id
        return h_msg

    def announce(self):
        print 'Announcing to tracker...'
        # TODO: served cached copies, add requests.get to reactor, add a response 
        #       handler that is called.

        # TODO: other params: 'numwant' 'ip'

        req_params = {
            'info_hash': self.info_hash,
            'peer_id': self.client.peer_id,
            'port': PORT,
            'uploaded': self.uploaded,
            'downloaded': self.downloaded,
            'left': self.bytes_left,
            'event': self.event,
            'compact': 1, # some trackers will refuse requests without 'compact=1'
        }

        if self.tracker_id:
            req_params['trackerid'] = self.trackerid

        tracker_url = self.metainfo['announce']
        self.handle_tracker_response(requests.get(tracker_url, params=req_params))

    def handle_tracker_response(self, req):
        if not req.ok:
            raise Exception('Problem with Tracker')

        # Note: req.text returns a 'utf-8' encoding of req.content.
        rd = bencode.bdecode(req.content)
        if 'failure_reason' in rd:
            raise Exception(rd['failure_reason'])

        self.interval = rd.get('interval', None)
        self.complete = rd.get('complete', None)
        self.incomplete = rd.get('incomplete', None)

        # Optional keys a tracker may return
        self.tracker_id = rd.get('tracker_id', self.tracker_id)
        self.min_interval = rd.get('min interval', None)

        # # Set the timeout of the reactor to the announce interval
        # if self.min_interval:
        #     self.reactor.timeout = self.min_interval
        # else:
        #     self.reactor.timeout = self.inteval

        peers_raw = rd['peers']
        if isinstance(peers_raw, dict):
            # Must then check peer_id matches  t handshake
            raise Exception('Dicitionary peers model not yet implemented.')

        # Break peers_raw into list of (ip, port) tuples
        peers_bytes = (peers_raw[i:i+6] for i in range(0, len(peers_raw), 6))
        peer_addrs = (map(ord, peer) for peer in peers_bytes)
        peers = [('.'.join(map(str, p[0:4])), p[4]*256 + p[5]) for p in peer_addrs]
        print peers
        self._update_peers(peers)

    def _update_peers(self, peers):
        """Provided a list of tuples of peers, attempt to establish a socket if
        we are not already connected to him."""
        existing_peers = [x.host_and_port() for x in self.peers]
        print existing_peers
        for peer in peers:
            if peer not in existing_peers:
                try:
                    p = Peer(peer[0], peer[1], atorrent=self)
                except socket.error, e:
                    continue

                self.peers.append(p)
                self.client.reactor.add_reader_writer(p)
