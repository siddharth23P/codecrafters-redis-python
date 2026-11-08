"""Clients parked on list keys (BLPOP). Driven by the event loop: nothing here sleeps."""
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Blocked:
    """Returned by a command instead of a reply: park this client until served or timed out."""
    keys: list                        # keys to wait on, in priority order
    timeout: float | None             # seconds; None = wait forever
    try_serve: Callable[[bytes], Any]  # key -> reply, or None if nothing to take yet
    on_timeout: Any = None            # reply sent when the timeout passes


@dataclass(eq=False)
class Waiter:
    blocked: Blocked
    deadline: float | None
    resume: Callable[[Any], None]  # sends the reply and unparks the client


class BlockingRegistry:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._by_key: dict[bytes, deque[Waiter]] = {}  # FIFO: first blocked, first served
        self._waiters: set[Waiter] = set()
        self._ready: set[bytes] = set()  # keys that got data since the last serve_ready()

    def block(self, blocked: Blocked, resume) -> Waiter:
        deadline = None if blocked.timeout is None else self._clock() + blocked.timeout
        waiter = Waiter(blocked, deadline, resume)
        for key in blocked.keys:
            self._by_key.setdefault(key, deque()).append(waiter)
        self._waiters.add(waiter)
        return waiter

    def cancel(self, waiter: Waiter):
        """Forget a waiter (served, timed out, or client disconnected)."""
        self._waiters.discard(waiter)
        for key in waiter.blocked.keys:
            queue = self._by_key.get(key)
            if queue and waiter in queue:
                queue.remove(waiter)
                if not queue:
                    del self._by_key[key]

    def notify(self, key: bytes):
        """Called by commands that add data to `key`. Serving happens later, in serve_ready()."""
        if key in self._by_key:
            self._ready.add(key)

    def serve_ready(self):
        """Hand new data to waiting clients, oldest first. Run after every command."""
        while self._ready:
            key = self._ready.pop()
            while (queue := self._by_key.get(key)):
                waiter = queue[0]
                reply = waiter.blocked.try_serve(key)
                if reply is None:  # list is empty again
                    break
                self.cancel(waiter)
                waiter.resume(reply)

    def next_timeout(self) -> float | None:
        """Seconds until the earliest deadline, or None if no waiter has one."""
        deadlines = [w.deadline for w in self._waiters if w.deadline is not None]
        if not deadlines:
            return None
        return max(0.0, min(deadlines) - self._clock())

    def tick(self):
        now = self._clock()
        expired = [w for w in self._waiters if w.deadline is not None and w.deadline <= now]
        for waiter in expired:
            self.cancel(waiter)
            waiter.resume(waiter.blocked.on_timeout)
