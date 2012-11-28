import logging

from client import client
from torrent import ActiveTorrent

def main():
    logging.basicConfig(filename='bt.log',
                        filemode='w',
                        level=logging.DEBUG,
                        # format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                        format='%(asctime)s - %(levelname)s - %(message)s')

    log = logging.getLogger('test_driver')
    log.info('Starting up...')

    client.add_torrent('tom.torrent')
    client.reactor.start()

if __name__ == '__main__':
    main()
