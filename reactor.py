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
        self.server.bind(('localhost', PORT))
        self.server.listen(QUEUED_CNXNS)

        self.readers = [self.server]
        self.writers = []
        self.excepts = []

        self.timeout = TIMEOUT

    def set_timeout(self, timeout):
        self.timeout = timeout

    def add_reader_writer(self, rwriter):
        self.readers.append(rwriter)
        self.writers.append(rwriter)

    def start(self):
        timeout = 10

        while self.readers or self.writers:
            reads, writes, excepts = select.select(self.readers, self.writers, self.excepts, timeout)

            print 'Reads: ', reads
            print 'Writes: ', writes
            print 'Excepts: ', excepts
            print

            # TODO: not right --- Timeout, announce to Tracker
            if not (reads or writes or excepts):
                print 'Timed out!'
                self.client.announce()
                continue

            for r in reads:
                if r is self.server:
                    print 'Peer attempting to connect to me!'
                    connection, peer_host = s.accept()
                    peer = Peer(self.client, peer_host[0], peer_host[1], connection)
                    self.add_reader_writer(peer)

                elif isinstance(r, Peer):
                    r.read_data()

            for w in writes:
                if isinstance(w, Peer):
                    w.write_data()


