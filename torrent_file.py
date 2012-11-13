import bencode
import math

from util import sha1_hash

class TorrentFile(object):
    def __init__(self, file_name, metainfo=None):
        """Constructs a TorrentFile by reading a .torrent file or
        using a info_dict. If metainfo is passsed, file_name is not read.

        Args:
            file_name (str)
        Kwargs:
            info_dict (dict)
        """
        # TODO: Error checking
        if not metainfo:
            with open(file_name, 'r') as f:
                contents = f.read()

        self.metainfo = metainfo if metainfo else bencode.bdecode(contents)
        self.info_dict = self.metainfo['info']
        self.info_hash = sha1_hash(str(bencode.bencode(self.info_dict)))

    @classmethod
    def create_torrent(cls, 
                       file_name, 
                       tracker_url, 
                       content, 
                       piece_length=512,
                       write=True):
        # TODO: add other options like: announce-list, creation date, comment, created by, encoding
        info_dict = {
            'name': file_name,
            'length': len(contents),
            # Fields common to single and multi-file below
            'piece_length': piece_length * 1024,
            'pieces': cls._pieces_hashes(contents)
        }

        metainfo = {
            'info': info_dict,
            'announce': tracker_url
        }

        if write:
            with open(file_name, 'w') as f:
                f.write(bencode.bencode(metainfo))

        return cls(file_name, metainfo)

    def get_length(self):
        # Single File
        if 'length' in self.info_dict:
            return self.info_dict['length']

        # Multi-file format (could be a single file)
        files = self.info_dict['files']
        return sum(f['length'] for f in files)

    @classmethod
    def _pieces_hashes(cls, string, piece_lenth):
        """Return array built from 20-byte SHA1 hashes
            of the string's pieces.
        """
        output = ""
        current_pos = 0
        num_bytes= len(string)
        while current_pos < num_bytes:
            if current_pos + piece_length > num_bytes:
                to_position = num_bytes
            else:
                to_position = current_pos + piece_length

            piece_hash = util.sha1_hash(string[current_pos:to_position])
            output += piece_hash
            current_pos += piece_length

        return output

    def _num_pieces(self, contents):
        length = len(contents)
        if length < self.piece_length:
            return 1
        else:
            return int(math.ceil(float(length) / self.piece_length))
