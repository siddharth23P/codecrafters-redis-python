"""Turn Python reply values into RESP bytes. Knows nothing about commands or sockets."""
from typing import Any, Callable

from .resp_types import ErrorReply, SimpleString

CRLF = b"\r\n"


class RespEncoder:
    """Encodes a value by dispatching on its exact type.

    Pass `extra` ({type: encode_fn}) to add or override types without editing this class.
    """

    def __init__(self, extra: dict[type, Callable[[Any], bytes]] | None = None):
        self._encoders: dict[type, Callable[[Any], bytes]] = {
            SimpleString: self._simple_string,
            ErrorReply: self._error,
            bytes: self._bulk_string,
            str: lambda v: self._bulk_string(v.encode()),
            int: self._integer,
            list: self._array,
            tuple: self._array,
            type(None): self._null,
        }
        self._encoders.update(extra or {})

    def encode(self, value: Any) -> bytes:
        encode_fn = self._encoders.get(type(value))
        if encode_fn is None:
            raise TypeError(f"cannot encode {type(value).__name__} as RESP")
        return encode_fn(value)

    def _simple_string(self, value: SimpleString) -> bytes:
        return b"+" + value.value.encode() + CRLF

    def _error(self, value: ErrorReply) -> bytes:
        return b"-" + value.message.encode() + CRLF

    def _bulk_string(self, value: bytes) -> bytes:
        return b"$%d\r\n%s\r\n" % (len(value), value)

    def _integer(self, value: int) -> bytes:
        return b":%d\r\n" % value

    def _array(self, value) -> bytes:
        return b"*%d\r\n" % len(value) + b"".join(self.encode(item) for item in value)

    def _null(self, value: None) -> bytes:
        return b"$-1\r\n"
