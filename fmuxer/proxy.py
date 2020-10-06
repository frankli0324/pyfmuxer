import socket
from select import select
from .utils import hexdump


class Proxy:
    def __init__(self, upstream: socket.socket, client: socket.socket):
        self.upstream = upstream
        self.client = client

    @staticmethod
    def proxy_send(sock_from, sock_to):
        buffer = sock_from.recv(1024)
        # hexdump(buffer)
        if not buffer:
            raise EOFError()
        while buffer:
            buffer = buffer[sock_to.send(buffer):]

    def serve_until_dead(self):
        while True:
            ready_read, ready_write, ready_exceptional = select(
                [self.upstream, self.client],
                [self.upstream, self.client],
                [], 1
            )
            if ready_exceptional:
                print(ready_exceptional)
                # what does it mean?
            if self.upstream in ready_read and self.client in ready_write:
                self.proxy_send(self.upstream, self.client)
            if self.client in ready_read and self.upstream in ready_write:
                self.proxy_send(self.client, self.upstream)
