import hashlib
from constants import BLOCK_SIZE

class Piece(object):
    def __init__(self, hash_val, num_blocks):
        self.hash_val = hash_val
        self.num_blocks = num_blocks
        self.blocks = [0] * num_blocks
        self.block_data = {}

    @property
    def full(self):
        return all(self.blocks)

    @property 
    def data(self):
        return ''.join(self.block_data[i] for i in range(self.num_blocks))

    def add(self, piece_offset, data):
        index = piece_offset / BLOCK_SIZE
        self.block_data[index] = data
        self.blocks[index] = 1 # TODO: what if data isn't guaranteed to be of BLOCK_SIZE?

    def has_block(self, piece_offset):
        """Return True if the given piece_offset falls within a block this 
        piece has, False otherwise"""
        index = piece_offset / BLOCK_SIZE
        return self.blocks[index] == 1

    def empty_blocks(self):
        """Return a list of piece_offset and length (i.e. block length) pairs
        that this piece doesn't have.

        Returns:
            list((int, int), ...): list of piece_offset and length tuples
        """
        empty = self._empty_block_nums(self.num_blocks)
        return map(lambda x: (x*BLOCK_SIZE, BLOCK_SIZE), empty)

    def validates(self):
        return self.hash_val == hashlib.sha1(self.data).digest()

    def _empty_block_nums(self, num_blocks):
        return filter(lambda x: not self.blocks[x],
                      (i for i in range(num_blocks)))

class FinalPiece(Piece):
    def __init__(self, hash_val, num_blocks, final_block_size):
        super(FinalPiece, self).__init__(hash_val, num_blocks)
        self.final_block_size = final_block_size

    def empty_blocks(self):
        last_block = self.num_blocks - 1
        empty_block_nums = self._empty_block_nums(last_block)
        empty_blocks = map(lambda x: (x*BLOCK_SIZE, BLOCK_SIZE), empty_block_nums)

        if not self.blocks[last_block]:
            empty_blocks.append((last_block*BLOCK_SIZE, self.final_block_size))

        return empty_blocks
