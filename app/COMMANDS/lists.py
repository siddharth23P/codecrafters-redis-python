"""List commands: RPUSH, LPUSH, LLEN, LRANGE, LPOP, BLPOP.

A list is stored as store[key] = [deque, expires_at].
"""
from collections import deque

from . import check_arity, register, registered_commands, to_int
from ..PROTOCOL.resp_types import Array, BulkString, CommandError, Integer, WrongTypeError
from ..SERVER.blocking import Blocked


def create(ctx):
    return registered_commands(ListCommands(ctx.store, ctx.blocking))


class ListCommands:
    def __init__(self, store, blocking):
        self._store = store
        self._blocking = blocking  # woken on push, used by BLPOP

    # --- commands ---

    @register
    def rpush(self, args):
        """RPUSH key element [element ...] -> new length"""
        return self._push(args, "rpush", deque.extend)

    @register
    def lpush(self, args):
        """LPUSH key element [element ...] -> new length; "a b c" ends up as c b a"""
        return self._push(args, "lpush", deque.extendleft)

    @register
    def llen(self, args):
        """LLEN key -> length of the list, 0 if missing"""
        check_arity(args, "llen", len(args) == 1)
        items = self._list(args[0])
        return Integer(len(items) if items is not None else 0)

    @register
    def lrange(self, args):
        """LRANGE key start stop -> elements from start to stop, both inclusive; -1 = last"""
        check_arity(args, "lrange", len(args) == 3)
        start, stop = to_int(args[1]), to_int(args[2])
        items = self._list(args[0])
        if items is None:
            return Array([])

        items = list(items)
        n = len(items)
        if start < 0:
            start = max(n + start, 0)
        if stop < 0:
            stop += n
        if stop < 0:  # still negative: range ends before the list starts
            return Array([])
        return Array(items[start:stop + 1])

    @register
    def lpop(self, args):
        """LPOP key [count] -> first element, or an array of up to count elements"""
        check_arity(args, "lpop", len(args) in (1, 2))
        count = to_int(args[1]) if len(args) == 2 else None
        items = self._list(args[0])
        if items is None:
            return BulkString(None)
        if count is None:
            return BulkString(items.popleft() if items else None)
        return Array([items.popleft() for _ in range(min(count, len(items)))])

    @register
    def blpop(self, args):
        """BLPOP key [key ...] timeout -> [key, element], or null array on timeout"""
        check_arity(args, "blpop", len(args) >= 2)
        *keys, timeout = args
        try:
            timeout = float(timeout)
        except ValueError:
            raise CommandError("timeout is not a float or out of range")
        if timeout < 0:
            raise CommandError("timeout is negative")

        for key in keys:  # first non-empty list wins
            items = self._list(key)
            if items:
                return Array([key, items.popleft()])
        return Blocked(keys, timeout or None)  # 0 = wait forever

    # --- shared helpers ---

    def _list(self, key):
        """The deque at key, or None if missing. Raise WrongTypeError if key holds a string."""
        entry = self._store.get(key)
        if entry is None:
            return None
        if not isinstance(entry[0], deque):
            raise WrongTypeError()
        return entry[0]

    def _push(self, args, name, add):
        check_arity(args, name, len(args) >= 2)
        key, *elements = args
        items = self._list(key)
        if items is None:
            items = deque()
            self._store[key] = [items, None]
        add(items, elements)
        self._blocking.notify(key)  # wake BLPOP clients waiting on this key
        return Integer(len(items))

