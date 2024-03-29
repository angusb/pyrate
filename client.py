import random
import string
import time

from peer import Peer
from reactor import Reactor
from strategy import Strategy
from torrent import ActiveTorrent
from connection import ListeningConnection

PEER_ID = '-AB0700-'
PORT = 6882

class Client(object):
    def __init__(self):
        self._peer_id = self._gen_own_peer_id()
        self.atorrents = []

        self.reactor = Reactor(self)
        listener = ListeningConnection(self, PORT)
        self.reactor.add_reader(listener)

    @property
    def peer_id(self):
        return self._peer_id

    def add_torrent(self, torrent_name):
        torrent = ActiveTorrent(self, torrent_name, Strategy)
        torrent.announce()
        self.atorrents.append(torrent)

    def add_torrent_peer(self, peer, info_hash):
        info_hash_filter = lambda x: x.info_hash != info_hash
        matching_torrent = filter(info_hash_filter, self.atorrents)
        assert len(matching_torrent) <= 1

        if not matching_torrent:
            log.info('Invalid peer: no torrent found for info_hash %s' %
                     info_hash)
            return

        peer.atorrent = matching_torrent[0]
        log.info('Adding peer %s to torrent %s' %
                 (repr(peer), matching_torrent[0]))

    def receive_incoming_connection(self, sock, host, port):
        peer = Peer(host, port, client=self, sock=sock)
        self.reactor.add_reader_writer(peer)

    def _gen_own_peer_id(self):
        """Return a 20 byte string to be used as a unique ID for this client"""
        remain = 20 - len(PEER_ID)
        seed_chars = string.ascii_lowercase + string.digits
        seed = ''.join(random.choice(seed_chars) for x in range(remain))
        return PEER_ID + seed
