import os
import logging

log = logging.getLogger('persistence')

class FileWriter(object):
    def __init__(self, filemgr, path, filesize):
        self.filemgr = filemgr
        self.filesize = filesize

        self.write_queue = []
        self.bytes_written = 0

        if isinstance(path, str):
            self.filename = path
        elif isinstance(path, list):
            self.filename = '/'.join(path) # OS independent?
            path = '/'.join(path.pop())
            if path and not os.path.exists(path):
                os.makedirs(path)
        else:
            raise TypeError("'path' must be of type str or list")

        self.file = open(self.filename, 'w+')

    def fileno(self):
        return self.file.fileno()

    def add_file_data(self, pos, data):
        self.write_queue.append((pos, data))
        self.filemgr.atorrent.client.reactor.reg_writer(self) # TODO: wow look at this chain...

    def write_data(self):
        for pos, data in self.write_queue:
            log.info('Writing data to %s at %d' % (self.filename, pos))
            self.file.seek(pos)
            self.file.write(data)
            self.bytes_written += len(data)

        self.write_queue = []
        self.filemgr.atorrent.client.reactor.unreg_writer(self)

        if self.bytes_written == self.filesize:
            log.info("File '%s' finished. Closing.." % self.filename)
            self.file.close()

class FileManager(object):
    def __init__(self, atorrent):
        self.atorrent = atorrent

        # Single file torrent or multi-file torrent
        if 'length' in atorrent.info_dict:
            self.file_writers = [FileWriter(self,
                                            atorrent.info_dict['name'],
                                            atorrent.info_dict['length'])]
            self.file_lengths = [atorrent.info_dict['length']]
        else:
            self.file_writers = []
            self.file_lengths = []
            for fd in atorrent.info_dict['files']:
                b = FileWriter(self, fd['path'], fd['length'])
                self.file_writers.append(b)
                self.file_lengths.append(fd['length'])

    def add_piece(self, piece_index, piece_data):
        absolute_offset = self.atorrent.info_dict['piece length'] * piece_index
        bytes_so_far = 0
        for fidx, fl in enumerate(self.file_lengths):
            if fl + bytes_so_far > absolute_offset:
                break
            bytes_so_far += fl

        relative_start = absolute_offset - bytes_so_far
        remaining_bytes = len(piece_data)
        data_iter = 0

        while remaining_bytes > 0:
            relative_end = min(self.file_lengths[fidx],
                               relative_start + remaining_bytes)
            num_bytes_to_write = relative_end - relative_start

            data_sgmt = piece_data[data_iter:data_iter + num_bytes_to_write]
            self.file_writers[fidx].add_file_data(relative_start, data_sgmt)

            log.info('Queueing FileWriter %s data for piece %d' %
                     (self.file_writers[fidx].filename, piece_index))

            remaining_bytes -= num_bytes_to_write
            data_iter += num_bytes_to_write
            relative_start = 0
            fidx += 1
