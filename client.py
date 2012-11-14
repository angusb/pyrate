import random
import string
import time
import socket

import requests
import bencode

from peer import Peer
from reactor import Reactor

PEER_ID = '-AB0700-'
PORT = 6882

class Client(object):
    def __init__(self):
        self.my_peer_id = self._gen_own_peer_id()
        self.downloaded = 0 # TODO: right place for this?
        self.uploaded = 0
        self.event = 'started'
        self.tracker_id = None
        self.reactor = Reactor(self)

        self.peers = []
        # self.numwant

    def set_torrent(self, torrent):
        self.torrent = torrent
        self.bytes_left = torrent.get_length()

    def handshake(self):
        pstrlen = chr(19)
        pstr = 'BitTorrent protocol'
        reserved = chr(0) * 8
        h_msg = pstrlen + pstr + reserved + self.torrent.info_hash + self.my_peer_id
        return h_msg

    def _gen_own_peer_id(self):
        """Return a 20 byte string to be used as a unique ID for this client"""
        remain = 20 - len(PEER_ID)
        seed_chars = string.ascii_lowercase + string.digits
        seed = ''.join(random.choice(seed_chars) for x in range(remain))
        return PEER_ID + seed

    def announce(self):
        print 'Announcing to tracker...'
        # TODO: served cached copies, add requests.get to reactor, add a response 
        #       handler that is called.

        # TODO: other params: 'numwant' 'ip'

        req_params = {
            'info_hash': self.torrent.info_hash,
            'peer_id': self.my_peer_id,
            'port': PORT,
            'uploaded': self.uploaded,
            'downloaded': self.downloaded,
            'left': self.bytes_left,
            'event': self.event,
            'compact': 1, # some trackers will refuse requests without 'compact=1'
        }

        if self.tracker_id:
            req_params['trackerid'] = self.trackerid

        tracker_url = self.torrent.metainfo['announce']
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
            # Must then check peer_id matches at handshake
            raise Exception('Dicitionary peers model not yet implemented.')

        # Break peers_raw into list of (ip, port) tuples
        peers_bytes = (peers_raw[i:i+6] for i in range(0, len(peers_raw), 6))
        peer_addrs = (map(ord, peer) for peer in peers_bytes)
        peers = [('.'.join(map(str, p[0:4])), p[4]*256 + p[5]) for p in peer_addrs]

        self._update_peers(peers)

    def _update_peers(self, peers):
        # # TODO remove...
        # ip_filter = lambda x: False if x[0] == '38.117.156.148' else True
        # peers = filter(ip_filter, peers)
        # print peers

        # Create a peer and add him to the list if he does not yet exist
        existing_peers = [x.host_and_port() for x in self.peers]
        print existing_peers
        for peer in peers:
            if peer not in existing_peers:
                try:
                    p = Peer(self, peer[0], peer[1])
                except socket.error, e:
                    continue

                self.peers.append(p)
                self.reactor.add_reader_writer(p)

    def connect_first_peer(self):
        if not self.peers:
            raise Exception('No peers!')

        host, port = self.peers[2]
        p = Peer(self, host, port)

