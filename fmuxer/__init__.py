import queue
import socket
import time
import traceback
from logging import getLogger
from selectors import DefaultSelector, EVENT_READ
from socketserver import BaseRequestHandler, ThreadingTCPServer
from typing import *

logger = getLogger('tmuxer')


class Rule:
    # bytes required for protocol identification
    required_bytes = 0
    # target to forward connection to, passed to socket.connect
    target = ()

    @property
    def name(self):
        return self.__class__.__name__

    # returns whether the protocol banner matched
    def match(self, banner) -> bool:
        return False

    def get_socket(self) -> socket.socket:
        try:
            assert isinstance(self.target, tuple)
            assert isinstance(self.target[0], str)
            assert isinstance(self.target[1], int)
        except AssertionError:
            logger.error('target must be a tuple ("host to connect to", port)')
            raise
        upstream = socket.socket()
        upstream.connect(self.target)
        return upstream

    # callback for per_forward actions, useful for content inspection
    def on_send(self, peer_from, peer_to, buffer) -> None:
        pass

    def on_error(self, err):
        traceback.print_exc()

    def __lt__(self, other):
        return self.required_bytes < other.required_bytes


class RequireMoreBytes(Exception):
    def __init__(self, rbytes, *args):
        super().__init__(*args)
        self.bytes = rbytes


class Proxy:
    def __init__(self, upstream: socket.socket, client: socket.socket, on_send: callable):
        self.upstream = upstream
        self.client = client
        self.on_send = on_send
        self.selector = DefaultSelector()
        self.selector.register(self.upstream, EVENT_READ, self.client)
        self.selector.register(self.client, EVENT_READ, self.upstream)

    def proxy_send(self, sock_from, sock_to):
        buffer = sock_from.recv(1024)
        if not buffer:
            raise EOFError()
        self.on_send(sock_from.getpeername(), sock_to.getpeername(), buffer)
        while buffer:
            buffer = buffer[sock_to.send(buffer):]

    def serve_until_dead(self):
        while True:
            for conn, mask in self.selector.select():
                self.proxy_send(conn.fileobj, conn.data)
            time.sleep(0.001)


class Handler(BaseRequestHandler):
    def muxer(self, sock) -> Optional[Tuple[Rule, socket.socket]]:
        q = queue.PriorityQueue()
        for rule in self.server.rules:
            q.put(rule)
        received_bytes = 0
        buf = b''
        upstream = None
        rule = None

        original_timeout = sock.gettimeout()
        sock.settimeout(5)  # TODO: be configurable?
        while not q.empty():
            rule = q.get()
            try:
                if rule.required_bytes > received_bytes:
                    buf += sock.recv(rule.required_bytes - received_bytes)
                    received_bytes = len(buf)
                if rule.match(buf):
                    upstream = rule.get_socket()
            except RequireMoreBytes as e:
                rule.required_bytes = e.bytes + received_bytes
                q.put(rule)
            except Exception as e:
                if e is socket.timeout and rule.on_timeout:
                    rule.on_timeout(e)
                upstream = rule.on_error(e)
            finally:
                if upstream:
                    break
        if not upstream:
            # no matches found
            return
        upstream.sendall(buf)
        sock.settimeout(original_timeout)
        return rule, upstream

    def handle(self):
        rule = None
        peer = f'{self.client_address[0]}:{self.client_address[1]}'
        try:
            context = self.muxer(self.request)
            if not context:
                logger.warning(f'<{peer}> no matches found')
                raise EOFError()
            rule, upstream = context
            logger.info(f'[{rule.name}] <{peer}> connected')
            proxy = Proxy(upstream, self.request, rule.on_send)
            proxy.serve_until_dead()
        except EOFError:
            logger.info(
                f'[{rule.name if rule else "no match"}] <{peer}> disconnected')

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
        traceback.print_exc()

    def register_rule(self, rule):
        assert isinstance(rule, Rule)
        self.rules.append(rule)

    def start(self):
        self.serve_forever()


__all__ = ['ForwardMuxer', 'RequireMoreBytes', 'Rule']
