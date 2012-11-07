from torrent_file import TorrentFile
from client import Client

def main():
	t = TorrentFile('ebook.torrent')
	c = Client()
	c.set_torrent(t)

	c.announce()

if __name__ == '__main__':
	main()
