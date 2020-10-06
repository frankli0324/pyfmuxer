import socket
from socketserver import BaseRequestHandler

from .proxy import Proxy


def Handler(muxer):
    class _Handler(BaseRequestHandler):

        def handle(self):
            try:
                upstream = muxer(self.request)
                if not upstream:
                    print('no matches found')
                    raise EOFError
                proxy = Proxy(upstream, self.request)
                proxy.serve_until_dead()
            except EOFError:
                print('disconnected')

        def finish(self):
            try:
                self.request.shutdown(socket.SHUT_RDWR)
                self.request.close()
            except:
                pass

    return _Handler
