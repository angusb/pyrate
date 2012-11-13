import socket
import select
import time

from peer import Peer

PORT = 6882
QUEUED_CNXNS = 20
TIMEOUT = 10

class Reactor(object):
    def __init__(self, client):
        self.client = client

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # huh?
        # self.server.setblocking(False)
        server.bind(('localhost', PORT))
        server.listen(QUEUED_CNXNS)

        self.readers = [self.server]
        self.writers = []
        self.excepts = []

        self.timeout = TIMEOUT

    def set_timeout(self, timeout):
        self.timeout = timeout

    def add_reader_writer(self, rwriter):
        readers.append(rwriter)
        writers.append(rwriter)

    def add_reader(self, reader):
        readers.append(reader)

    def add_writer(self, writer):
        readers.append(writer)

    def start(self):
        timeout = 10

        while self.readers or self.writers:
            reads, writes, excepts = select.select(self.readers, self.writers, self.excepts, timeout)

            # TODO: not right --- Timeout, announce to Tracker
            if not (reads or writes or excepts):
                print 'timed out'
                self.client.announce()
                continue

            for s in reads:
                if s is self.server:
                    connection, peer_host = s.accept()
                    peer = Peer(self.client, peer_host[0], peer_host[1], connection)
                    self.add_reader_writer(peer)

                elif s isinstance(Peer):
                    peer.read_data()

            for w in writes:
                if w isinstance(Peer):
                    peer.write_data()


