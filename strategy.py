import logging

from message import Msg
from piece import FinalPiece
from constants import BLOCK_SIZE

log = logging.getLogger('strategy')

# TODO: REQUESTED PIECES
# 
# Right now we aren't using self.requested_pieces when picking a new piece.
# requested_pieces is suppose to prevent us from request the same piece
# from multiple clients, however, it should be more granular to support blocks
# because if some clients have part of a piece (but collectively they don't) have
# the piece, multiple requests for the same piece (different block) should be 
# sent out

# TODO make abstract to enforce interface

# Threshold at which we should request a piece from every peer
REQ_THRESHOLD = 10

class Strategy(object):
    def __init__(self, atorrent):
        self.atorrent = atorrent

        self.has_pieces = set()
        self.wants_pieces = set(range(atorrent.num_pieces()))
        self.requested_pieces = set()

    def add_piece_block(self, piece_index, offset, data):
        """Adds a block of data at an offset of a particular piece. Returns
        True if the block piece was succesfully added as the last block of
        the piece, False otherwise.

        Args:
            piece_index (int): piece to add block of data to
            offset (int): offset within block to store data
            data (str): binary data

        Returns:
            bool
        """
        piece = self.atorrent.pieces[piece_index]

        if piece.full or piece.has_block(offset):
            log.info('Receiving piece data that we already have...')
            return False

        if len(data) != BLOCK_SIZE and not isinstance(piece, FinalPiece): # TODO
            log.critical('Receiving an odd block size - %d' % len(data))
            return False

        piece.add(offset, data)

        # If the piece is now full, we have some state to update        
        if piece.full:
            self.has_pieces.add(piece_index)
            self.wants_pieces.discard(piece_index)
            self.requested_pieces.discard(piece_index)
            if piece.validates():
                return True
                # return Msg('have', index=piece_index) # TODO: broadcast
            else:
                print 'hash check doesn\'t validate'
                log.warning('Hash check on piece %d doesn\'t validate' % piece_index)
                return False
                # TODO. drop the piece
        return False

    def am_interested(self, peer):
        """Returns True if the strategy says we should be interested in a 
        peer, False otherwise."""
        relevant_pieces = peer.pieces.intersection(self.wants_pieces)
        if relevant_pieces or len(self.wants_pieces) < REQ_THRESHOLD:
            return True

        return False

    def get_next_request(self, peer):
        relevant_pieces = peer.pieces.intersection(self.wants_pieces)
        if relevant_pieces:
            piece_num_to_fetch = relevant_pieces.pop()
        else:
            if len(self.wants_pieces) < REQ_THRESHOLD:
                piece_num_to_fetch = self.wants_pieces.pop()
                self.wants_pieces.add(piece_num_to_fetch)           
            else:
                return []
            
        piece = self.atorrent.pieces[piece_num_to_fetch]
        assert not piece.full, 'Set logic is broken'

        msgs = [
            Msg('request',
                index=piece_num_to_fetch,
                begin=begin,
                length=length)
            for begin, length in piece.empty_blocks()
            ]

        return msgs

    # TODO: Place in ActiveTorrent
    def get_bitfield(self):
        bitfield = ''
        groups_of_eight = map(lambda x: range(x, x+8),
                              range(0, self.atorrent.num_pieces(), 8))
        for group in groups_of_eight:
            bvls = map(lambda x: 2**x[0] if x[1] in self.has_pieces else 0,
                       enumerate(group))
            byte = chr(sum(bvls))
            bitfield += byte

        return bitfield
