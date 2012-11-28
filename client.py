import random
import string
import time

from reactor import Reactor
from strategy import Strategy
from torrent import ActiveTorrent

PEER_ID = '-AB0700-'
print 'yoyoma'

class Client(object):
    def __init__(self):
        self._peer_id = self._gen_own_peer_id()
        self.reactor = Reactor(self)
        self.atorrents = []

    @property
    def peer_id(self):
        return self._peer_id

    def add_torrent(self, torrent_name):
        torrent = ActiveTorrent(self, torrent_name, Strategy)
        torrent.announce()
        self.atorrents.append(torrent)

    def set_torrent(self, torrent):
        self.strategy = Strategy(torrent)
        self.torrent = torrent

    def _gen_own_peer_id(self):
        """Return a 20 byte string to be used as a unique ID for this client"""
        remain = 20 - len(PEER_ID)
        seed_chars = string.ascii_lowercase + string.digits
        seed = ''.join(random.choice(seed_chars) for x in range(remain))
        return PEER_ID + seed

# Expose singleton object
client = Client()
