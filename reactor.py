import socket
import select
import time

from peer import Peer

PORT = 6881
QUEUED_CNXNS = 20
TIMEOUT = 10

class Reactor(object):
    def __init__(self, client):
        self.client = client

        self.readers = set()
        self.writers = set()
        self.excepts = set()

        self.timeout = TIMEOUT

    def set_timeout(self, timeout):
        self.timeout = timeout

    def reg_writer(self, writer):
        self.writers.add(writer)

    def unreg_writer(self, writer):
        if writer not in self.writers:
            print 'unregging writer that does not exist'
        self.writers.discard(writer)

    def add_reader(self, reader):
        self.readers.add(reader)

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
                # TODO: self.client.announce()
                continue

            for r in reads:
                r.read_event()

            for w in writes:
                w.write_data()


