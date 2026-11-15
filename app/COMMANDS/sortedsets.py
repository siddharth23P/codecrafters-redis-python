import time
from collections import OrderedDict

from ..PROTOCOL.resp_types import Array, BulkString, CommandError, WrongTypeError
from ..SERVER.blocking import Blocked
from . import check_arity, register, registered_commands, to_int
from ..DATASTRUCTURES.sortedsets import SortedSet

MIN_ID = (0, 0)
MAX_ID = (float("inf"), float("inf"))


def create(ctx):
    return registered_commands(SortedSetsCommands(ctx.store, ctx.blocking))


class SortedSetsCommands:
    def __init__(self, store, blocking):
        self._store = store
        self._blocking = blocking
    
    def _zinit(self, key):
        entries = self._store.get(key)
        if entries is None:
            entries = SortedSet()
            self._store[key] = entries
        elif not isinstance(entries, SortedSet):
            raise WrongTypeError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return entries
    
    @register
    def zadd(self, args):
        check_arity("zadd", len(args) >= 3 and len(args) % 2 == 1)
        key, *pairs = args
        entries = self._zinit(key)
        key_added = 0
        for i in range(0, len(pairs), 2):
            score = float(pairs[i])
            member = pairs[i + 1]
            if entries.search(score) is None:
                entries.insert(member, score)
                key_added += 1
        return key_added