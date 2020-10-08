# this is a ruleset for hiding a minecraft server behind an http server
# also, the http handler dumps the traffic in the hex form

import logging

import coloredlogs

from fmuxer import *
from fmuxer.utils import hexdump

server = ForwardMuxer('0.0.0.0', 80)


class HTTPHandler(Rule):
    name = 'HTTP'
    required_bytes = 7
    target = ('localhost', 81)

    def match(self, banner) -> bool:
        for method in [b'GET', b'POST', b'PATCH', b'PUT', b'OPTIONS', b'HEAD']:
            if banner.startswith(method):
                return True
        return False

    def on_send(self, peer_from, peer_to, buffer) -> None:
        if logger.getEffectiveLevel() == 10:  # debug
            logger.debug(f'from {peer_from} to {peer_to}\n' + hexdump(buffer))


class MCHandler(Rule):
    name = 'Minecraft'
    required_bytes = 5
    target = ('localhost', 25565)

    @staticmethod
    def read_varint(banner):
        number = 0
        pos = 0
        for i in range(0, 5):
            number |= (int(banner[i]) & 0x7F) << 7 * i
            if not int(banner[i]) & 0x80:
                pos = i + 1
                break
        if number & (1 << 31):
            number -= 1 << 32
        if not ((-1 << 31) <= number < (+1 << 31)):
            return 0, None
        return pos, number

    def match(self, banner):
        try:
            off, packet_length = self.read_varint(banner)

            if not packet_length:
                return False
            if len(banner) - 2 < packet_length:
                raise RequireMoreBytes(packet_length - len(banner) + 2)

            off, packet_id = self.read_varint(banner[off:])
            off, version = self.read_varint(banner[off:])
            off, addr_len = self.read_varint(banner[off:])

            if addr_len + off > packet_length:
                return False
            off += addr_len
            port = int.from_bytes(banner[off:off + 2], 'big')
            off, next_state = self.read_varint(banner[off + 2:])
            if next_state != 1 and next_state != 2:
                return False
        except IndexError:
            return False
        return True


logger = logging.getLogger('fmuxer')
coloredlogs.install(level='DEBUG')

server.register_rule(MCHandler())
server.register_rule(HTTPHandler())
server.start()
