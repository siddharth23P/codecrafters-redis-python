"""Stream commands: XADD, XRANGE, XREAD.

A stream is stored as store[key] = [OrderedDict(id -> {field: value}), None], ids ascending.
An id is b"<ms>-<seq>"; ids compare as (ms, seq) tuples.
"""
import time
from collections import OrderedDict

from ..PROTOCOL.resp_types import Array, BulkString, CommandError, WrongTypeError
from ..SERVER.blocking import Blocked
from . import check_arity, register, registered_commands, to_int

MIN_ID = (0, 0)
MAX_ID = (float("inf"), float("inf"))


def create(ctx):
    return registered_commands(StreamCommands(ctx.store, ctx.blocking))


class StreamCommands:
    def __init__(self, store, blocking):
        self._store = store
        self._blocking = blocking  # woken on XADD, used by XREAD BLOCK

    # --- commands ---

    @register
    def xadd(self, args):
        """XADD key id field value [field value ...] -> the new entry's id. id may be * or <ms>-*."""
        check_arity("xadd", len(args) >= 4 and len(args) % 2 == 0)
        key, raw_id, *pairs = args
        entries = self._stream(key)
        last = _parse_id(next(reversed(entries))) if entries else MIN_ID
        new = _next_id(raw_id, last)
        if new == MIN_ID:
            raise CommandError("The ID specified in XADD must be greater than 0-0")
        if new <= last:
            raise CommandError("The ID specified in XADD is equal or smaller than the target stream top item")

        if entries is None:
            entries = OrderedDict()
            self._store[key] = [entries, None]
        entry_id = b"%d-%d" % new
        entries[entry_id] = dict(zip(pairs[::2], pairs[1::2]))
        self._blocking.notify(key)  # wake XREAD BLOCK clients waiting on this key
        return BulkString(entry_id)

    @register
    def xrange(self, args):
        """XRANGE key start end -> entries with start <= id <= end; - and + are the min and max."""
        check_arity("xrange", len(args) == 3)
        key, start, end = args
        return Array(self._range(key, _parse_id(start, 0), _parse_id(end, float("inf"))))

    @register
    def xread(self, args):
        """XREAD [BLOCK ms] STREAMS key [key ...] id [id ...] -> [[key, entries], ...] with id > given id.

        Streams with no new entries are left out; null if none have any. "$" means the stream's last id.
        """
        timeout_ms = None
        if args and args[0].lower() == b"block":
            check_arity("xread", len(args) >= 2)
            timeout_ms = to_int(args[1])
            if timeout_ms < 0:
                raise CommandError("timeout is negative")
            args = args[2:]
        if not args or args[0].lower() != b"streams":
            raise CommandError("syntax error")
        streams = args[1:]
        check_arity("xread", streams and len(streams) % 2 == 0)

        half = len(streams) // 2
        keys = streams[:half]
        starts = [self._after(key, raw) for key, raw in zip(keys, streams[half:])]  # resolve $ now

        def read(_key=None):
            found = []
            for key, start in zip(keys, starts):
                if entries := self._range(key, start, MAX_ID):
                    found.append(Array([key, Array(entries)]))
            return Array(found) if found else None

        reply = read()
        if reply is not None or timeout_ms is None:
            return reply if reply is not None else Array(None)
        return Blocked(keys, timeout_ms / 1000 or None, read)  # BLOCK 0 = wait forever

    # --- shared helpers ---

    def _stream(self, key):
        """The OrderedDict at key, or None if missing. Raise WrongTypeError for other types."""
        entry = self._store.get(key)
        if entry is None:
            return None
        if not isinstance(entry[0], OrderedDict):
            raise WrongTypeError()
        return entry[0]

    def _range(self, key, lo, hi):
        """[[id, [field, value, ...]], ...] for entries with lo <= id <= hi."""
        result = []
        for entry_id, fields in (self._stream(key) or {}).items():
            current = _parse_id(entry_id)
            if current > hi:
                break  # ordered, so nothing later matches
            if current >= lo:
                flat = [x for pair in fields.items() for x in pair]  # {a: 1, b: 2} becomes [a, 1, b, 2]
                result.append(Array([entry_id, Array(flat)]))
        return result

    def _after(self, key, raw):
        """Smallest id strictly greater than raw. "$" means the stream's current last id."""
        if raw == b"$":
            entries = self._stream(key)
            raw = next(reversed(entries)) if entries else b"0-0"
        ms, seq = _parse_id(raw, 0)
        return ms, seq + 1


def _parse_id(raw, default_seq=0):
    """b"5-3" gives (5, 3); b"5" gives (5, default_seq); b"-" and b"+" are the min and max."""
    if raw == b"-":
        return MIN_ID
    if raw == b"+":
        return MAX_ID
    ms, sep, seq = raw.partition(b"-")
    try:
        return int(ms), int(seq) if sep else default_seq
    except ValueError:
        raise CommandError("Invalid stream ID specified as stream command argument") from None


def _next_id(raw, last):
    """The (ms, seq) XADD should use for raw, given the stream's last id."""
    if raw == b"*":
        ms = max(time.time_ns() // 1_000_000, last[0])
        return ms, last[1] + 1 if ms == last[0] else 0
    ms_part, sep, seq_part = raw.partition(b"-")
    if sep and seq_part == b"*":
        ms = _parse_id(ms_part)[0]
        return ms, last[1] + 1 if ms == last[0] else 0
    return _parse_id(raw)
