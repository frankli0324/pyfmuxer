# pyfmuxer

An extendable forward proxy and muxer written in Python

## features

* in Python3 with built-in modules, zero dependency
* customizable by registering protocols
* traffic analisis

## Example

```python
import socket

from fmuxer import ForwardMuxer

server = ForwardMuxer('0.0.0.0', 1234)


def SSHHandler(b, more):
    if b.startswith(b'SSH'):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 22))
        return sock


def HTTPHandler(b, more):
    for method in [b'GET', b'POST', b'PATCH', b'PUT', b'OPTIONS', b'HEAD']:
        if b.startswith(method):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', 81))
            return sock


server.register_handler(3, SSHHandler)
server.register_handler(7, HTTPHandler)
server.start()
```
