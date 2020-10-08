import queue
import socket
import time
import traceback
import typing
from select import select
from socketserver import BaseRequestHandler, ThreadingTCPServer

from .log import logger


class ComparableRule(dict):
    def __lt__(self, other):
        return self['required_bytes'] < other['required_bytes']


class RequireMoreBytes(Exception):
    def __init__(self, rbytes, *args):
        super().__init__(*args)
        self.bytes = rbytes


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
                logger.debug(ready_exceptional)
                # what does it mean?
            if self.upstream in ready_read and self.client in ready_write:
                self.proxy_send(self.upstream, self.client)
            if self.client in ready_read and self.upstream in ready_write:
                self.proxy_send(self.client, self.upstream)
            time.sleep(0.001)


class Handler(BaseRequestHandler):
    def muxer(self, sock) -> typing.Optional[socket.socket]:
        q = queue.PriorityQueue()
        for rule in self.server.rules:
            q.put(ComparableRule(rule))
        received_bytes = 0
        buf = b''
        upstream = None
        original_timeout = sock.gettimeout()
        sock.settimeout(5)  # TODO: be configurable?
        while not q.empty():
            rule = q.get()
            try:
                if rule['required_bytes'] > received_bytes:
                    buf += sock.recv(rule['required_bytes'] - received_bytes)
                    received_bytes = len(buf)
                upstream = rule['get_socket'](buf)
            except RequireMoreBytes as e:
                rule['required_bytes'] = e.bytes + received_bytes
                q.put(rule)
            except Exception as e:
                if e is socket.timeout and rule['on_timeout']:
                    rule['on_timeout'](e)
                upstream = rule['on_error'](e)
            finally:
                if upstream:
                    break
        if not upstream:
            # no matches found
            return
        upstream.sendall(buf)
        sock.settimeout(original_timeout)
        return upstream

    def handle(self):
        peer = f'{self.client_address[0]}:{self.client_address[1]}'
        try:
            upstream = self.muxer(self.request)
            if not upstream:
                logger.warning('no matches found')
                raise EOFError()
            logger.info(f'{peer} connected')
            proxy = Proxy(upstream, self.request)
            proxy.serve_until_dead()
        except EOFError:
            logger.info(f'{peer} disconnected')

    def finish(self):
        try:
            self.request.shutdown(socket.SHUT_RDWR)
            self.request.close()
        except:
            pass


class ForwardMuxer(ThreadingTCPServer):
    allow_reuse_address = True
    request_queue_size = 1

    def __init__(self, host: str, port: int, rules: list = None):
        self.bind_addr = (host, port)
        self.rules = rules or []
        super().__init__(self.bind_addr, Handler)

    def service_actions(self):
        # todo: cleanup threads
        pass

    def handle_error(self, request, client_address):
        import sys
        logger.error(sys.exc_info())
        logger.error(client_address)

    def register_handler(
            self,
            required_bytes: int,
            get_socket: callable,
            on_connection: callable = lambda c: None,
            on_timeout: callable = None,
            on_error: callable = lambda e: traceback.print_exc(),
    ):
        """
        Adds a new protocol matching rule to the list of rules.

        :parameter required_bytes: bytes required for protocol identification
        :parameter get_socket: returns socket connection if matched the rule, None if not
        :param on_connection: callback for per_proxy actions, useful for content inspection
        :param on_timeout: fallback action when timeout occurs. if not defined, `on_error` is used.
        :param on_error: rules can define their fallback action when error occurs on receiving
            the first few bytes (e.g. timeout). defaults to lambda: None
        """
        self.rules.append({
            "required_bytes": required_bytes,
            "get_socket": get_socket,
            "on_connection": on_connection,
            "on_timeout": on_timeout or on_error,
            "on_error": on_error,
        })
        pass

    def start(self):
        self.serve_forever()


__all__ = ['ForwardMuxer', 'RequireMoreBytes']
