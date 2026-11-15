"""Turn reply values into RESP bytes."""
from .resp_types import (
    Array,
    BulkString,
    ErrorReply,
    Integer,
    Raw,
    SimpleString,
    ToMaster,
)


def encode(value) -> bytes:
    match value:
        case Raw():
            return value.data
        case ToMaster() | Integer() | BulkString():
            return encode(value.value)
        case SimpleString():
            return b"+%s\r\n" % value.value.encode()
        case ErrorReply():
            return b"-%s\r\n" % value.message.encode()
        case Array(items=None):
            return b"*-1\r\n"
        case Array():
            return encode(list(value.items))
        # plain Python values
        case None:
            return b"$-1\r\n"
        case int():
            return b":%d\r\n" % value
        case str():
            return encode(value.encode())
        case bytes():
            return b"$%d\r\n%s\r\n" % (len(value), value)
        case list() | tuple():
            return b"*%d\r\n" % len(value) + b"".join(encode(item) for item in value)
    raise TypeError(f"cannot encode {type(value).__name__} as RESP")
