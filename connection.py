import socket

QUEUED_CNXNS = 5

class ListeningConnection(object):
    def __init__(self, client, port):
        self.client = client
        self.port = port

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # TODO
        # self.server.setblocking(False)
        self.sock.bind(('localhost', port))
        self.sock.listen(QUEUED_CNXNS)

    def fileno(self):
        """Gives the illusion that this object is a file descriptor."""
        return self.sock.fileno()

    def read_event(self):
        connection, (ip, port) = self.sock.accept()
        self.client.receive_incoming_connection(connection, ip, port)
