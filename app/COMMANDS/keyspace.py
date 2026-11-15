"""Commands on keys of any type: TYPE, KEYS."""
from collections import OrderedDict, deque

from ..PROTOCOL.resp_types import CommandError, SimpleString
from . import check_arity, register, registered_commands


def create(ctx):
    return registered_commands(KeyspaceCommands(ctx.store))


class KeyspaceCommands:
    def __init__(self, store):
        self._store = store

    @register
    def type(self, args):
        """TYPE key -> +string, +list, +stream, or +none"""
        check_arity("type", len(args) == 1)
        entry = self._store.get(args[0])
        if entry is None:
            return SimpleString("none")
        if isinstance(entry[0], deque):
            return SimpleString("list")
        if isinstance(entry[0], OrderedDict):
            return SimpleString("stream")
        return SimpleString("string")

    @register
    def keys(self, args):
        """KEYS * -> every key. Other patterns are not supported."""
        check_arity("keys", len(args) == 1)
        if args[0] != b"*":
            raise CommandError("Only '*' pattern is supported in KEYS command")
        return list(self._store)
