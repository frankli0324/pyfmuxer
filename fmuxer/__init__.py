import traceback

from .handler import Handler
from .muxer import Muxer, RequireMoreBytes
from .server import ThreadedTCPMuxerServer


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
        ThreadedTCPMuxerServer(
            self.bind_addr, Handler(Muxer(self.rules))
        ).serve_forever()


__all__ = ['ForwardMuxer', 'RequireMoreBytes']
