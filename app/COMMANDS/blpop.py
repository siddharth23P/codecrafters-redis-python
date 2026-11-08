from collections import deque

from ..blocking import Blocked
from ..resp_types import Array, CommandError, ErrorReply


def create(ctx):
    store = ctx.store

    def pop_from(key):
        """Pop the head of the list at key -> [key, element], or None if empty or missing."""
        entry = store.get(key)
        if entry is None or not isinstance(entry[0], deque) or not entry[0]:
            return None
        return Array([key, entry[0].popleft()])

    def run(args):
        """BLPOP key [key ...] timeout -> [key, element], or null array on timeout."""
        if len(args) < 2:
            raise CommandError("wrong number of arguments for 'blpop' command")
        *keys, timeout = args
        try:
            timeout = float(timeout)
        except ValueError:
            raise CommandError("timeout is not a float or out of range")
        if timeout < 0:
            raise CommandError("timeout is negative")

        for key in keys:  # first non-empty list wins
            if key in store and not isinstance(store[key][0], deque):
                return ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")
            reply = pop_from(key)
            if reply is not None:
                return reply

        return Blocked(keys, None if timeout == 0 else timeout, pop_from, on_timeout=Array(None))

    return run
