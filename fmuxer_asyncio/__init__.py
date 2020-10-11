import asyncio
import queue
import traceback
from logging import getLogger
from typing import *

logger = getLogger('tmuxer_asyncio')


class Rule:
    # bytes required for protocol identification
    required_bytes = 0
    # target to forward connection to, passed to socket.connect
    target = ()

    @property
    def name(self):
        return self.__class__.__name__

    # returns whether the protocol banner matched
    def match(self, banner) -> bool:
        return False

    async def get_socket(self) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        try:
            assert isinstance(self.target, tuple)
            assert isinstance(self.target[0], str)
            assert isinstance(self.target[1], int)
        except AssertionError:
            logger.error('target must be a tuple ("host to connect to", port)')
            raise
        return await asyncio.open_connection(*self.target)
        # callback for per_forward actions, useful for content inspection

    def on_send(self, peer_from, peer_to, buffer) -> None:
        pass

    def on_error(self, err):
        traceback.print_exc()

    def __lt__(self, other):
        return self.required_bytes < other.required_bytes


class RequireMoreBytes(Exception):
    def __init__(self, rbytes, *args):
        super().__init__(*args)
        self.bytes = rbytes


class Proxy:
    def __init__(self, lreader, lwriter, rreader, rwriter, on_send):
        self.upstream = self._pipe(lreader, rwriter)
        self.downstream = self._pipe(rreader, lwriter)
        self.on_send = on_send
        self.other = {
            rwriter.get_extra_info('peername'): lwriter.get_extra_info('peername'),
            lwriter.get_extra_info('peername'): rwriter.get_extra_info('peername')
        }

    async def _pipe(self, reader, writer):
        try:
            while not reader.at_eof():
                content = await reader.read(1024)
                if content:
                    self.on_send(
                        self.other[writer.get_extra_info('peername')],
                        writer.get_extra_info('peername'),
                        content
                    )
                writer.write(content)
        finally:
            writer.close()
            raise EOFError()

    async def serve_until_dead(self):
        await asyncio.gather(self.upstream, self.downstream)


class ForwardMuxerAsyncio:
    def __init__(self, host: str, port: int, rules: list = None):
        self.bind_addr = (host, port)
        self.rules = rules or []

    async def muxer(self, lreader) -> Optional[Tuple[Rule, Tuple[asyncio.StreamReader, asyncio.StreamWriter]]]:
        q = queue.PriorityQueue()
        for rule in self.rules:
            q.put(rule)

        received_bytes = 0
        buf = b''
        upstream = None
        rule = None
        while not q.empty():
            rule = q.get()
            try:
                if rule.required_bytes > received_bytes:
                    buf += await asyncio.wait_for(lreader.read(
                        rule.required_bytes - received_bytes
                    ), timeout=5)
                    received_bytes = len(buf)
                if rule.match(buf):
                    upstream = await rule.get_socket()
            except RequireMoreBytes as e:
                rule.required_bytes = e.bytes + received_bytes
                q.put(rule)
            except Exception as e:
                if e is asyncio.TimeoutError and rule.on_timeout:
                    rule.on_timeout(e)
                upstream = rule.on_error(e)
            finally:
                if upstream:
                    break
        if not upstream:
            # no matches found
            return
        upstream[1].write(buf)
        return rule, upstream

    async def handle(self, lreader, lwriter):
        peer = lwriter.get_extra_info('peername')
        peer = f'{peer[0]}:{peer[1]}'
        try:
            context = await self.muxer(lreader)
            if not context:
                logger.warning(f'<{peer}> no matches found')
                logger.info(f'[no match] <{peer}> disconnected')
                return
            rule, (rreader, rwriter) = context
            logger.info(f'[{rule.name}] <{peer}> connected')
            proxy = Proxy(lreader, lwriter, rreader, rwriter, rule.on_send)
            await proxy.serve_until_dead()
        except EOFError:
            logger.info(f'[{rule.name}] <{peer}> disconnected')

    async def get_server(self):
        return await asyncio.start_server(self.handle, *self.bind_addr)

    def register_rule(self, rule):
        assert isinstance(rule, Rule)
        self.rules.append(rule)

    def start(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.get_server())
        loop.run_forever()


__all__ = ['ForwardMuxerAsyncio', 'RequireMoreBytes', 'Rule']
