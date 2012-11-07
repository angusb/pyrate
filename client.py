import socket
import random
import string
import time
import util
import requests

import bencode

PEER_ID = '-AB0700-'
PORT = 6882

class Client(object):
    def __init__(self):
        self.my_peer_id = self._gen_own_peer_id()
        self.downloaded = 0 # TODO: right place for this?
        self.uploaded = 0
        self.event = 'started'
        self.tracker_id = None
        # self.numwant

    def set_torrent(self, torrent):
        self.torrent = torrent
        self.bytes_left = torrent.get_length()

    def handshake(self, peer_id):
        pstrlen = chr(19)
        pstr = 'BitTorrent protocol'
        reserved = '\x00\x00\x00\x00\x00\x00\x00\x00'
        h_msg = pstrlen + pstr + self.torrent.info_hash + self.my_peer_id

    def peer_handshake(self, h_msg):
        pstrlen = h_msg[0]
        pstr = payload[1:20]
        reserved = payload[20:28]
        info_hash = payload[28:48]
        peer_id = payload[48:68]

    def _gen_own_peer_id(self):
        """Return a 20 byte string to be used as a unique ID for this client"""
        remain = 20 - len(PEER_ID)
        seed_chars = string.ascii_lowercase + string.digits
        seed = ''.join(random.choice(seed_chars) for x in range(remain))
        return PEER_ID + seed

    def announce(self):
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

        rd = bencode.bdecode(req.text)
        if 'failure_reason' in rd:
            raise Exception(rd['failure_reason'])

        self.interval = rd.get('interval', None)
        self.complete = rd.get('complete', None)
        self.incomplete = rd.get('incomplete', None)

        # Optional keys a tracker may return
        self.tracker_id = rd.get('tracker_id', self.tracker_id)
        self.min_interval = rd.get('min interval', None)

        peers_raw = rd['peers']
        if isinstance(peers_raw, dict):
            raise Exception('Dicitionary peers model not yet implemented.')

        peers_bytes = (peers_raw[i:i+6] for i in range(0, len(peers_raw), 6))
        peer_addrs = (map(ord, peer) for peer in peers_bytes)
        peers = ['.'.join(map(str, p[0:4])) + ':' + str(p[4]*256 + p[5]) for p in peer_addrs]

        return peers


