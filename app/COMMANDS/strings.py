"""String commands: SET, GET.

A string is stored as store[key] = (value, expires_at or None).
"""
import time

from . import check_arity, register, registered_commands
from ..PROTOCOL.resp_types import CommandError, SimpleString

UNITS = {b"px": 1 / 1000, b"ex": 1}  # option -> seconds per unit


def create(ctx):
    return registered_commands(StringCommands(ctx.store))


class StringCommands:
    def __init__(self, store):
        self._store = store

    @register
    def set(self, args):
        """SET key value [PX ms | EX s] -> +OK"""
        check_arity(args, "set", len(args) in (2, 4))
        key, value, *option = args
        expires_at = None
        if option:
            unit, amount = option
            scale = UNITS.get(unit.lower())
            if scale is None or not amount.isdigit() or int(amount) == 0:
                raise CommandError("Syntax Error")
            expires_at = time.monotonic() + int(amount) * scale

        self._store[key] = (value, expires_at)
        return SimpleString("OK")

    @register
    def get(self, args):
        """GET key -> value, or null if missing or expired"""
        check_arity(args, "get", len(args) == 1)
        entry = self._store.get(args[0])  # None encodes as $-1 (null)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and time.monotonic() >= expires_at:
            del self._store[args[0]]  # lazy expiry: remove on read
            return None
        return value
    
    @register
    def keys(self, args):
        """KEYS pattern -> list of keys matching the pattern"""
        check_arity(args, "keys", len(args) == 1)
        pattern = args[0]
        if pattern == b'*':
            return list(self._store.keys())
        else:
            raise CommandError("Only '*' pattern is supported in KEYS command")
