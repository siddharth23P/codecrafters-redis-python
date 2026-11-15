"""String commands: SET, GET, INCR.

A string is stored as store[key] = (value, expires_at or None), expires_at on time.monotonic().
"""
import time

from ..PROTOCOL.resp_types import CommandError, Integer, SimpleString, WrongTypeError
from . import check_arity, register, registered_commands, to_int

UNITS = {b"px": 1 / 1000, b"ex": 1}  # option -> seconds per unit


def create(ctx):
    return registered_commands(StringCommands(ctx.store))


class StringCommands:
    def __init__(self, store):
        self._store = store

    @register
    def set(self, args):
        """SET key value [PX ms | EX s] -> +OK"""
        check_arity("set", len(args) in (2, 4))
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
        check_arity("get", len(args) == 1)
        entry = self._entry(args[0])
        return entry[0] if entry else None  # None encodes as $-1 (null)

    @register
    def incr(self, args):
        """INCR key -> value after adding 1; a missing key counts as 0. Keeps the key's expiry."""
        check_arity("incr", len(args) == 1)
        key = args[0]
        value, expires_at = self._entry(key) or (b"0", None)
        value = to_int(value) + 1
        self._store[key] = (str(value).encode(), expires_at)
        return Integer(value)

    def _entry(self, key):
        """(value, expires_at) for a live string key, else None. Expired keys are deleted (lazy expiry)."""
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and time.monotonic() >= expires_at:
            del self._store[key]
            return None
        if not isinstance(value, bytes):
            raise WrongTypeError()
        return entry
