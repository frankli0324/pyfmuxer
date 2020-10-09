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

    offset = 0
    banner = b''

    def read_varint(self):
        number = 0
        pos = 0
        for i in range(self.offset, self.offset + 5):
            number |= (int(self.banner[i]) & 0x7F) << 7 * (i - self.offset)
            if not int(self.banner[i]) & 0x80:
                pos = i + 1
                break
        if number & (1 << 31):
            number -= 1 << 32
        if not ((-1 << 31) <= number < (+1 << 31)):
            return 0, None
        self.offset = pos
        return number

    def match(self, banner):
        try:
            self.offset = 0
            self.banner = banner
            packet_length = self.read_varint()

            if not packet_length:
                return False
            if len(banner) - self.offset - 1 < packet_length:
                raise RequireMoreBytes(
                    packet_length - len(banner) + self.offset + 1)

            packet_id = self.read_varint()
            version = self.read_varint()
            addr_len = self.read_varint()

            if addr_len + self.offset > packet_length:
                return False
            self.offset += addr_len + 2
            port = int.from_bytes(banner[self.offset - 2:self.offset], 'big')

            next_state = self.read_varint()
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
