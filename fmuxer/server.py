from socketserver import ThreadingMixIn, TCPServer


class ThreadedTCPMuxerServer(ThreadingMixIn, TCPServer):
    allow_reuse_address = True
    request_queue_size = 1

    def service_actions(self):
        # todo: cleanup threads
        pass

    def handle_error(self, request, client_address):
        import sys
        print(sys.exc_info())
        print(client_address)
