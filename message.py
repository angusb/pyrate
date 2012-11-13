import struct

MSG_IDS = {
    0: 'choke',
    1: 'unchoke',
    2: 'interested',
    3: 'not_interested',
    4: 'have',
    5: 'bitfield',
    6: 'request',
    7: 'piece',
    8: 'cancel',
    9: 'port'
}

MSG_ARGS = {
    'keep_alive': (),
    'choke': (),
    'unchoke': (),
    'interested': (),
    'not_interested': (),
    'have': ('index',),
    'bitfield': ('bitfield',),
    'request': ('index', 'begin', 'length'),
    'piece': ('index', 'begin', 'block'),
    'cancel': ('index', 'begin', 'length'),
    'port': ('port',),
    'handshake': ('info_hash', 'peer_id'), # Other components are standardized
}

class Msg(object):
    def __init__(self, kind, **kwargs):
        if kind not in MSG_ARGS:
            raise TypeError('__init__() not a valid kind of message')

        for arg in MSG_ARGS[kind]:
            try:
                setattr(self, arg, kwargs[arg])
            except KeyError:
                raise TypeError('__init__() for %s Msg requires arg %s' % (kind, arg))

    @property
    def kind(self):
        return self._kind

    @property
    def bytestring(self):
        return getattr(self, '_' + self._kind)()

    def __len__(self):
        return len(self.bytestring)

    def __str__(self):
        return self.bytestring

    def __repr__(self):
        s = 'Msg(\'' + self._kind + '\''
        for att in MSG_ARGS[self._kind]:
            s += ', '
            s += att + '=' + repr(getattr(self, att))
        s += ')'
        return s

    def _form_message(self, kind, payload=''):
        message_id = chr(kind) # TODO necessary?
        prefix = struct.pack('!I', len(message_id) + len(payload))
        return prefix + message_id + payload

    def _keep_alive(self):
        return '\x00' * 4

    def _choke(self):
        return self._form_message(0)

    def _unchoke(self):
        return self._form_message(1)

    def _interested(self):
        return self._form_message(2)

    def _not_interested(self):
        return self._form_message(3)

    def _have(self):
        return self._form_message(4, struct.pack('!I', self.index))

    def _bitfield(self):
        return self._form_message(5, self.bitfield)

    def _request(self):
        return self._form_message(6, struct.pack('!III', self.index, self.begin, self.length))

    def _piece(self):
        payload = struct.pack('!II', self.index, self.begin)
        payload += self.block
        return self._form_message(7, payload)

    def _cancel(self):
        return self._form_message(8, struct.pack('!III', self.index, self.begin, self.length))

    def _port(self):
        return self._form_message(9, struct.pack('!III', self.port))

    def _handshake(self):
        # Following parameters don't vary
        pstrlen = chr(19)
        pstr = 'BitTorrent protocol'
        rsrvd = chr(0)*8
        return ''.join([pstrlen, pstr, rsrvd, self.info_hash, self.peer_id])

def parse_message(buff):
    """Takes a str buffer and returns a tuple of a Msg object and the
    remainder of the buffer. If a Msg cannot be formed, return a tuple of
    (None, buff)

    Args:
        buff (str): buffer to parse

    Returns:
        tuple (Msg, str): if a Msg cannot be formed, return (None, buff)
    """
    if not buff or len(buff) < 4:
        return None, buff

    # Handshake doesn't follow the normal protocol
    if len(buff) >= 5 and buff[:5] == '\x13BitT':
        if len(buff) >= 49+19 and buff[1:20] == 'BitTorrent protocol':
            info_hash = buff[28:48]
            peer_id = buff[48:68]
            rest = buff[68:]
            return Msg('handshake', info_hash=info_hash, peer_id=peer_id), rest

        return None, buff

    msg_length = struct.unpack('!I', buff[:4])[0]
    if len(buff) < msg_length + 4:
        return None, buff

    rest = buff[msg_length+4:]
    if msg_length == 0:
        return Msg('keep_alive'), rest

    msg_id = ord(buff[4])
    msg_kind = MSG_IDS[msg_id]

    if msg_kind in ['choke', 'unchoke', 'interested', 'not_interested']:
        return Msg(msg_kind), rest

    elif msg_kind == 'have':
        (index,) = struct.unpack('!I', buff[5:9])
        return Msg('have', index=index), rest

    elif msg_kind == 'bitfield':
        return Msg('bitfield', bitfield=buff[5:msg_length+4]), rest

    elif msg_kind in ['request', 'cancel']:
        index, begin, length = struct.unpack('!III', buff[5:msg_length+4])
        return Msg(msg_kind, index=index, begin=begin, length=length), rest

    elif msg_kind == 'piece':
        index, begin = struct.unpack('!II', buff[5:13])
        return Msg('piece', index=index, begin=begin, block=buff[13:msg_length+4]), rest

    elif msg_kind == 'port':
        port, _ = struct.unpack('!H', buff[5:7])
        return Msg('port', port=port), rest

    else:
        raise Exception('unknown message type \'%s\' encountered' % msg_kind)
