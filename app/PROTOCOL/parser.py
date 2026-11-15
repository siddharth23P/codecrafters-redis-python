"""RESP (Redis Serialization Protocol) parser."""

CRLF = b"\r\n"


class Incomplete(Exception):
    """Buffer doesn't hold a full message yet; wait for more bytes."""


class ProtocolError(Exception):
    """Bytes are not valid RESP."""


def parse(buf: bytes, pos: int = 0):
    """Parse one RESP value starting at buf[pos]. Return (value, position just after it)."""
    end = buf.find(CRLF, pos)
    if end == -1:
        raise Incomplete
    marker, header, pos = buf[pos:pos + 1], buf[pos + 1:end], end + 2

    if marker == b"+":
        return header.decode(), pos
    if marker == b"-":
        return RuntimeError(header.decode()), pos
    if marker == b":":
        return _to_int(header), pos
    if marker == b"$":
        length = _to_int(header)
        if length == -1:
            return None, pos
        end = pos + length
        if len(buf) < end + 2:
            raise Incomplete
        if buf[end:end + 2] != CRLF:
            raise ProtocolError("bulk string length does not match its data")
        return buf[pos:end], end + 2  # sliced by length, so data may contain \r\n
    if marker == b"*":
        size = _to_int(header)
        if size == -1:
            return None, pos
        items = []
        for _ in range(size):
            item, pos = parse(buf, pos)
            items.append(item)
        return items, pos
    raise ProtocolError(f"unknown RESP type {marker!r}")


def _to_int(header: bytes) -> int:
    try:
        return int(header)
    except ValueError:
        raise ProtocolError(f"expected integer, got {header!r}") from None
