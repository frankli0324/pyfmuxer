import queue
import socket
from typing import Optional


class ComparableRule(dict):
    def __lt__(self, other):
        return self['required_bytes'] < other['required_bytes']


class RequireMoreBytes(Exception):
    def __init__(self, rbytes, *args):
        super().__init__(*args)
        self.bytes = rbytes


def Muxer(rules):
    def _Muxer(sock: socket.socket) -> Optional[socket.socket]:
        q = queue.PriorityQueue()
        for rule in rules:
            q.put(ComparableRule(rule))

        received_bytes = 0
        buf = b''
        upstream = None
        original_timeout = sock.gettimeout()
        sock.settimeout(5)  # TODO: be configurable?
        # logger.debug(buf)
        while not q.empty():
            rule = q.get()
            try:
                if rule['required_bytes'] > received_bytes:
                    buf += sock.recv(rule['required_bytes'] - received_bytes)
                    received_bytes = len(buf)

                upstream = rule['get_socket'](buf)
            except RequireMoreBytes as e:
                rule['required_bytes'] = e.bytes
                q.put(rule)
            except Exception as e:
                if e is socket.timeout and rule['on_timeout']:
                    rule['on_timeout'](e)
                upstream = rule['on_error'](e)
            finally:
                if upstream:
                    print(rule['get_socket'].__name__)
                    break
        if not upstream:
            # no matches found
            return
        upstream.sendall(buf)
        sock.settimeout(original_timeout)
        return upstream

    return _Muxer
