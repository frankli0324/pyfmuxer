from .handler import Handler
from .muxer import Muxer
from .server import ThreadedTCPMuxerServer
import traceback


class ForwardMuxer:

    def __init__(self, host: str, port: int, rules: list = None):
        self.bind_addr = (host, port)
        self.rules = rules or []

    def register_handler(
            self,
            required_bytes: int,
            get_socket: callable,
            on_connection: callable = lambda c: None,
            on_timeout: callable = None,
            on_error: callable = lambda e: traceback.print_exc(),
    ):
        self.rules.append({
            "required_bytes": required_bytes,
            "get_socket": get_socket,
            "on_connection": on_connection,
            "on_timeout": on_timeout or on_error,
            "on_error": on_error,
        })
        pass

    def start(self):
        ThreadedTCPMuxerServer(
            self.bind_addr, Handler(Muxer(self.rules))
        ).serve_forever()


__all__ = ['ForwardMuxer']
