"""Reply types a command can return, beyond plain Python values.

Plain values map to RESP as: bytes/str -> bulk string, int -> integer,
list -> array, None -> null bulk string.
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


class CommandError(Exception):
    """Raised by a command for bad usage; sent to the client as `-ERR <message>`."""
