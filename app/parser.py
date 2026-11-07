"""RESP (Redis Serialization Protocol) parser.

Design:
- BufferReader   : reads raw bytes from a buffer (lines, fixed-size chunks).
- TypeParser     : abstract strategy that decodes one RESP type.
- *Parser classes: one concrete strategy per RESP type.
- RespParser     : picks the right strategy for each marker byte.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Iterable


class Incomplete(Exception):
    """Buffer doesn't hold a full message yet; wait for more bytes."""


class ProtocolError(Exception):
    """Bytes are not valid RESP."""


class BufferReader:
    """Cursor over a byte buffer. Knows bytes and delimiters, nothing about RESP types."""

    DELIMITER = b"\r\n"

    def __init__(self, buffer: bytes):
        self._buf = buffer
        self._pos = 0

    @property
    def position(self) -> int:
        """Number of bytes consumed so far."""
        return self._pos

    def read_line(self) -> bytes:
        """Return bytes up to the next delimiter (exclusive) and move past it."""
        end = self._buf.find(self.DELIMITER, self._pos)
        if end == -1:
            raise Incomplete
        line = self._buf[self._pos:end]
        self._pos = end + len(self.DELIMITER)
        return line

    def read_exact(self, n: int) -> bytes:
        """Return exactly n bytes followed by a delimiter and move past both."""
        end = self._pos + n
        if len(self._buf) < end + len(self.DELIMITER):
            raise Incomplete
        if self._buf[end:end + len(self.DELIMITER)] != self.DELIMITER:
            raise ProtocolError("bulk string length does not match its data")
        data = self._buf[self._pos:end]
        self._pos = end + len(self.DELIMITER)
        return data


def _to_int(header: bytes) -> int:
    try:
        return int(header)
    except ValueError:
        raise ProtocolError(f"expected integer, got {header!r}") from None


class TypeParser(ABC):
    """Decodes one RESP type. Subclasses set `marker` and implement `parse`."""

    marker: bytes

    @abstractmethod
    def parse(self, header: bytes, reader: BufferReader, parse_next: Callable[[], Any]) -> Any:
        """Decode a value.

        header     : bytes after the marker on the first line.
        reader     : source for any further bytes the type needs.
        parse_next : parses the next full value (for container types).
        """


class SimpleStringParser(TypeParser):
    marker = b"+"

    def parse(self, header, reader, parse_next):
        return header.decode()


class ErrorParser(TypeParser):
    marker = b"-"

    def parse(self, header, reader, parse_next):
        return RuntimeError(header.decode())


class IntegerParser(TypeParser):
    marker = b":"

    def parse(self, header, reader, parse_next):
        return _to_int(header)


class BulkStringParser(TypeParser):
    marker = b"$"

    def parse(self, header, reader, parse_next):
        length = _to_int(header)
        if length == -1:
            return None
        return reader.read_exact(length)


class ArrayParser(TypeParser):
    marker = b"*"

    def parse(self, header, reader, parse_next):
        size = _to_int(header)
        if size == -1:
            return None
        return [parse_next() for _ in range(size)]


DEFAULT_TYPE_PARSERS: tuple[TypeParser, ...] = (
    SimpleStringParser(),
    ErrorParser(),
    IntegerParser(),
    BulkStringParser(),
    ArrayParser(),
)


class RespParser:
    """Parses one RESP value from a buffer by dispatching on its marker byte.

    Stateless between calls, so one instance can serve every connection.
    Pass `type_parsers` to add or replace RESP types without editing this class.
    """

    def __init__(self, type_parsers: Iterable[TypeParser] = DEFAULT_TYPE_PARSERS):
        self._parsers = {p.marker: p for p in type_parsers}

    def parse(self, buffer: bytes) -> tuple[Any, int]:
        """Return (value, bytes_consumed). Raise Incomplete if more data is needed."""
        reader = BufferReader(buffer)
        value = self._parse_value(reader)
        return value, reader.position

    def _parse_value(self, reader: BufferReader) -> Any:
        line = reader.read_line()
        marker, header = line[:1], line[1:]
        type_parser = self._parsers.get(marker)
        if type_parser is None:
            raise ProtocolError(f"unknown RESP type {marker!r}")
        return type_parser.parse(header, reader, lambda: self._parse_value(reader))
