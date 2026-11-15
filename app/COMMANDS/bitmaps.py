"""Bitmap commands: SETBIT, GETBIT. They read and write string values, so SET/GET see the same bytes."""
import time

from ..PROTOCOL.resp_types import CommandError, Integer, WrongTypeError
from . import check_arity, register, registered_commands
from ..DATASTRUCTURES.bitmaps import BitMaps


def create(ctx):
    return registered_commands(BitMapsCommands(ctx.store))


class BitMapsCommands:
    def __init__(self, store):
        self._store = store
        self._bitmaps = BitMaps()

    @register
    def setbit(self, args):
        """SETBIT key offset value -> the bit's old value"""
        check_arity("setbit", len(args) == 3)
        key, offset, value = args
        offset = _offset(offset)
        try:
            value = int(value)
        except ValueError:
            value = -1
        if value not in (0, 1):
            raise CommandError("bit is not an integer or out of range")

        data, expires_at = self._entry(key) or (b"", None)
        bitmap = bytearray(data)
        old = self._bitmaps.setbit(bitmap, offset, value)
        self._store[key] = (bytes(bitmap), expires_at)
        return Integer(old)

    @register
    def getbit(self, args):
        """GETBIT key offset -> 0 or 1; missing key or offset past the end is 0"""
        check_arity("getbit", len(args) == 2)
        key, offset = args
        offset = _offset(offset)
        entry = self._entry(key)
        return Integer(self._bitmaps.getbit(entry[0], offset) if entry else 0)
    
    @register
    def strlen(self, args):
        """STRLEN key -> length of the string value, or 0 if missing"""
        check_arity("strlen", len(args) == 1)
        key = args[0]
        entry = self._entry(key)
        return Integer(len(entry[0]) if entry else 0)

    def _entry(self, key):
        """(value, expires_at) for a live string key, else None. Expired keys are deleted."""
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


def _offset(arg):
    try:
        offset = int(arg)
    except ValueError:
        offset = -1
    if offset < 0:
        raise CommandError("bit offset is not an integer or out of range")
    return offset
