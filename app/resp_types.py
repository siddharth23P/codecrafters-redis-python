"""Reply types a command can return, one class per RESP2 type.

Plain values still work and map to the same types:
bytes/str -> BulkString, int -> Integer, list/tuple -> Array, None -> null BulkString.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SimpleString:
    """Reply sent as `+value` (status replies such as OK or PONG)."""
    value: str


@dataclass(frozen=True)
class ErrorReply:
    """Reply sent as `-message`."""
    message: str


@dataclass(frozen=True)
class Integer:
    """Reply sent as `:value`."""
    value: int


@dataclass(frozen=True)
class BulkString:
    """Reply sent as `$len` + data; binary-safe. None is sent as the null bulk string `$-1`."""
    value: bytes | None


@dataclass(frozen=True)
class Array:
    """Reply sent as `*count` + each item encoded. None is sent as the null array `*-1`."""
    items: list | tuple | None


class CommandError(Exception):
    """Raised by a command for bad usage; sent to the client as `-ERR <message>`."""
