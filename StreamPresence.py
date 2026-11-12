"""Bounded, best-effort presence for the direct stream's web player."""
import re
import time


class StreamPresence:
    MAX_VIEWERS = 16
    TIMEOUT = 20.0

    def __init__(self, publish, clock=time.monotonic):
        self.publish = publish
        self.clock = clock
        self.viewers = {}

    async def update(self, viewer, action):
        if not re.fullmatch(r'[0-9a-f]{32}', viewer or '') or action not in ('join', 'heartbeat', 'quit'):
            return False
        if action == 'quit':
            if viewer in self.viewers:
                del self.viewers[viewer]
                await self.publish('gdo_stream_quit', viewer)
            return True
        if viewer not in self.viewers:
            if len(self.viewers) >= self.MAX_VIEWERS:
                return False
            self.viewers[viewer] = self.clock()
            await self.publish('gdo_stream_joined', viewer)
        else:
            self.viewers[viewer] = self.clock()
        return True

    async def expire(self, all_viewers=False):
        now = self.clock()
        for viewer, last in list(self.viewers.items()):
            if all_viewers or now - last >= self.TIMEOUT:
                del self.viewers[viewer]
                await self.publish('gdo_stream_quit', viewer)
