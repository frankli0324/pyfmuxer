# pyfmuxer

An extendable forward proxy and muxer written in Python

## features

* in Python3 with built-in modules, zero dependency
* customizable by registering protocols
* traffic analysis

## Usage

You have to extend the module with your own script

under most circumstances, you only have to import the ForwardMuxer class and instantiate it with address and port to bind to (see example), then register your protocol matching rules.

`ForwardMuxer.register_handler` requires two parameters, followed with three optional parameters. See docstring for explanations.

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
