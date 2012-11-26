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

        self.readers = set([self.server])
        self.writers = set()
        self.excepts = set()

        self.timeout = TIMEOUT

    def set_timeout(self, timeout):
        self.timeout = timeout

    def reg_writer(self, writer):
        if writer in self.writers:
            print 'reging writer that already exists'
        self.writers.add(writer)

    def unreg_writer(self, writer):
        if writer not in self.writers:
            print 'unregging writer that does not exist'
        self.writers.discard(writer)

    def add_reader_writer(self, rwriter):
        self.readers.add(rwriter)
        self.writers.add(rwriter)

    def remove_reader_writer(self, rwriter):
        if rwriter not in self.readers:
            print 'Removing a reader that was not in Reactor\'s readers'

        self.writers.remove(rwriter)
        self.readers.remove(rwriter)

    def start(self):
        timeout = 10

        while self.readers or self.writers:
            reads, writes, excepts = select.select(self.readers, self.writers, self.excepts, timeout)

            # print 'Reads: ', reads
            # print 'Writes: ', writes
            # print 'Excepts: ', excepts
            # print

            # TODO: not right --- Timeout, announce to Tracker
            if not (reads or writes or excepts):
                print 'Timed out!'
                self.client.announce()
                continue

            for r in reads:
                if r is self.server:
                    print 'Peer attempting to connect to me!'
                    connection, (ip, port) = s.accept()
                    peer = Peer(self.client, ip, port, connection)
                    self.add_reader_writer(peer)

                elif isinstance(r, Peer):
                    r.read_data()

            for w in writes:
                if isinstance(w, Peer):
                    w.write_data()


