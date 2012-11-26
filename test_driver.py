import logging

from torrent_file import TorrentFile
from client import Client

def main():
    logging.basicConfig(filename='bt.log',
                        filemode='w',
                        level=logging.DEBUG,
                        # format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                        format='%(asctime)s - %(levelname)s - %(message)s')

    log = logging.getLogger('test_driver')
    log.info('Starting up...')

    t = TorrentFile('tom.torrent')
    c = Client()
    c.set_torrent(t)

    c.announce()
    c.reactor.start()

if __name__ == '__main__':
    main()
