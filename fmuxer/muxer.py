import socket


def Muxer(rules):
    def _Muxer(sock: socket.socket) -> socket.socket:
        received_bytes = 0
        buf = b''
        upstream = None
        original_timeout = sock.gettimeout()
        sock.settimeout(5)  # TODO: be configurable?
        # logger.debug(buf)
        # {
        #     # bytes required for protocol identification
        #     "required_bytes": int,
        #     # returns socket connection if matched the rule, None if not
        #     "get_socket": callable,
        #     # callback for per_proxy actions, useful for content inspection
        #     "on_connection": callable,
        #     # fallback action when timeout occurs. if not defined on_error is used.
        #     # defaults to lambda: None
        #     "on_timeout": callable,
        #     # rules can define their fallback action when error occurs on receiving the first few bytes (e.g. timeout)
        #     # defaults to lambda: None
        #     "on_error": callable,
        # }
        # 改进思路：按照required bytes排序，放到优先队列里，如果有人要require more bytes，则放回优先队列
        for rule in rules:
            try:
                if rule['required_bytes'] > received_bytes:
                    buf += sock.recv(rule['required_bytes'] - received_bytes)
                    received_bytes = len(buf)

                def require_more_bytes(cnt):
                    nonlocal received_bytes, buf, sock
                    buf += sock.recv(cnt)
                    received_bytes = len(buf)
                    return buf

                upstream = rule['get_socket'](buf, require_more_bytes)
            except Exception as e:
                if e is socket.timeout and rule['on_timeout']:
                    rule['on_timeout'](e)
                upstream = rule['on_error'](e)
            finally:
                if upstream:
                    break
            # upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # upstream.connect(('192.168.1.182', 25565))
        if not upstream:
            # no matches found
            return
        upstream.sendall(buf)
        sock.settimeout(original_timeout)
        return upstream

    return _Muxer
