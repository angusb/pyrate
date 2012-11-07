import urllib2
import urllib
import time
import torrent_file
import client
import util
import bencode

class Tracker(object):
    def __init__(self, torrent):
        self.torrent = torrent
        self.info_hash = util.sha1_hash(str(bencode.bencode(self._info_dict['info']))),

    def connect(self, port=6969):
        """Make HTTP GET to tracker
        """
        params = {
            'info_hash': self.info_hash,
            'peer_id': self._peer.peer_id,
            'port': port,
            'uploaded': 0,
            'downloaded': 0,
            'left': info_dict['info']['length'],
            'event': 'started'
        }
        full_url = self._torrent_file.tracker_url + ":" + str(port)
        get_url = full_url + "?" + urllib.urlencode(params)
        print get_url
        req = urllib2.urlopen(get_url)

    def _handle_request(self, resp):
        rd = bencode.bdecode(resp)
        if rd.get('failure_reason', None):
            raise Exception(rd['failure_reason'])

        self.interval = rd.get['interval']
        self.complete = rd.get['complete']
        self.incomplete = rd.get['incomplete']

        # Optional keys a tracker may return
        self.tracker_id = rd.get('tracker_id', None)
        self.min_interval = rd.get('min_interval', None)

    def parse_response(self, response):
        response = bencode.bdecode(response)
        return response

