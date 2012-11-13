from torrent_file import TorrentFile
from client import Client

def main():
	t = TorrentFile('tom.torrent')
	c = Client()
	c.set_torrent(t)

	c.announce()
	c.connect_first_peer()

if __name__ == '__main__':
	main()
