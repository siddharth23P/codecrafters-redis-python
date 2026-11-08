"""Bookkeeping for clients parked by BLPOP. Nothing here sleeps or touches sockets."""
import time
from collections import deque
from dataclasses import dataclass

from ..PROTOCOL.resp_types import Array


@dataclass
class Blocked:
    """Returned by BLPOP instead of a reply: park this client."""
    keys: list
    timeout: float | None  # seconds; None = wait forever


class BlockingRegistry:
    def __init__(self, store):
        self._store = store
        self._queues: dict[bytes, deque] = {}  # key -> clients waiting on it, oldest first
        self._waiting: dict = {}               # client -> (keys, deadline or None)
        self._ready: set[bytes] = set()        # keys pushed to since the last served()

    def wait(self, client, blocked: Blocked):
        deadline = None if blocked.timeout is None else time.monotonic() + blocked.timeout
        self._waiting[client] = (blocked.keys, deadline)
        for key in blocked.keys:
            self._queues.setdefault(key, deque()).append(client)

    def remove(self, client):
        keys, _ = self._waiting.pop(client, ((), None))
        for key in keys:
            queue = self._queues.get(key)
            if queue and client in queue:
                queue.remove(client)
                if not queue:
                    del self._queues[key]

    def notify(self, key: bytes):
        """Called by RPUSH/LPUSH after adding to key."""
        if key in self._queues:
            self._ready.add(key)

    def served(self):
        """Pop elements for waiting clients. Return [(client, reply)], oldest client first."""
        replies = []
        while self._ready:
            key = self._ready.pop()
            items = self._store[key][0]
            while items and key in self._queues:
                client = self._queues[key][0]
                self.remove(client)
                replies.append((client, Array([key, items.popleft()])))
        return replies

    def timed_out(self):
        """Remove clients past their deadline. Return [(client, null array reply)]."""
        now = time.monotonic()
        expired = [c for c, (_, deadline) in self._waiting.items()
                   if deadline is not None and deadline <= now]
        for client in expired:
            self.remove(client)
        return [(client, Array(None)) for client in expired]

    def next_timeout(self):
        """Seconds until the earliest deadline, or None if no client has one."""
        deadlines = [d for _, d in self._waiting.values() if d is not None]
        return max(0.0, min(deadlines) - time.monotonic()) if deadlines else None
