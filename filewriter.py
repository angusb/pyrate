import logging
log = logging.getLogger('filewriter')

class FileWriter(object):
	def __init__(self, atorrent):
		self.atorrent = atorrent
		self.write_queue = []
		self.file = open('tmp', 'w+')

	def add_piece(self, piece_index, piece_data):
		# print 'called with piece_index', piece_index
		pos = self.atorrent.info_dict['piece length'] * piece_index
		self.write_queue.append((pos, piece_data))
		self.atorrent.client.reactor.reg_writer(self)		

	def fileno(self):
		return self.file.fileno()

	def write_data(self):
		for pos, data in self.write_queue:
			piece_num = pos / self.atorrent.info_dict['piece length']
			log.info('Writing data to pos %d' % piece_num)
			self.file.seek(pos)
			self.file.write(data)

		self.write_queue = []
		self.atorrent.client.reactor.unreg_writer(self)

	# def read_event(self):
	# 	pass
