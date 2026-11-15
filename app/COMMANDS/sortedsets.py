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
            if entries.add(member, score):
                key_added += 1
        return key_added
    
    @register
    def zrank(self, args):
        check_arity("zrank", len(args) == 2)
        key, member = args
        entries = self._store.get(key)
        if entries is None:
            return None
        elif not isinstance(entries, SortedSet):
            raise WrongTypeError("WRONGTYPE Operation against a key holding the wrong kind of value")
        rank = entries.rank(member)
        return rank
    
    @register
    def zrange(self, args):
        check_arity("zrange", len(args) in (3, 4))
        key, start, stop = args[:3]
        withscores = len(args) == 4 and args[3].lower() == b"withscores"
        entries = self._store.get(key)
        if entries is None:
            return []
        elif not isinstance(entries, SortedSet):
            raise WrongTypeError("WRONGTYPE Operation against a key holding the wrong kind of value")
        start, stop = to_int(start), to_int(stop)
        result = entries.range(start, stop)
        if withscores:
            return [BulkString(member) for member, score in result] + [BulkString(str(score).encode()) for member, score in result]
        else:
            return [BulkString(member) for member, score in result]
    
    @register
    def zcard(self, args):
        check_arity("zcard", len(args) == 1)
        key = args[0]
        entries = self._store.get(key)
        if entries is None:
            return 0
        elif not isinstance(entries, SortedSet):
            raise WrongTypeError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return len(entries)
    
    @register
    def zscore(self, args):
        check_arity("zscore", len(args) == 2)
        key, member = args
        entries = self._store.get(key)
        if entries is None:
            return None
        elif not isinstance(entries, SortedSet):
            raise WrongTypeError("WRONGTYPE Operation against a key holding the wrong kind of value")
        score = entries.score(member)
        if score is None:
            return None
        return BulkString(str(score).encode())
    
    @register
    def zrem(self, args):
        check_arity("zrem", len(args) >= 2)
        key, *members = args
        entries = self._store.get(key)
        if entries is None:
            return 0
        elif not isinstance(entries, SortedSet):
            raise WrongTypeError("WRONGTYPE Operation against a key holding the wrong kind of value")
        removed = 0
        for member in members:
            if member in entries:
                entries.remove(member)
                removed += 1
        return removed
        
    