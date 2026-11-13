"""Load an RDB snapshot from disk into the store at startup.

Only string values are supported. Expiry timestamps in the file are unix epoch;
the store uses time.monotonic(), so each one is converted on load.
"""
import os
import struct
import time

OP_AUX = 0xFA          # metadata: name, value
OP_RESIZEDB = 0xFB     # hash table sizes: two lengths
OP_EXPIRETIME_MS = 0xFC  # 8-byte little-endian unix ms
OP_EXPIRETIME = 0xFD   # 4-byte little-endian unix seconds
OP_SELECTDB = 0xFE     # db index: length
OP_EOF = 0xFF

TYPE_STRING = 0


class RDBError(Exception):
    pass


class _Reader:
    def __init__(self, data):
        self._data = data
        self._pos = 0

    def read(self, n):
        if self._pos + n > len(self._data):
            raise RDBError("unexpected end of file")
        chunk = self._data[self._pos:self._pos + n]
        self._pos += n
        return chunk

    def byte(self):
        return self.read(1)[0]

    def length(self):
        """Return (value, is_special). Special means `value` is a string-encoding id."""
        first = self.byte()
        kind = first >> 6
        if kind == 0b00:
            return first & 0x3F, False
        if kind == 0b01:
            return ((first & 0x3F) << 8) | self.byte(), False
        if kind == 0b10:
            if first == 0x80:
                return struct.unpack(">I", self.read(4))[0], False
            if first == 0x81:
                return struct.unpack(">Q", self.read(8))[0], False
            raise RDBError(f"bad length byte {first:#x}")
        return first & 0x3F, True

    def string(self):
        n, special = self.length()
        if not special:
            return self.read(n)
        if n == 0:
            return str(struct.unpack("<b", self.read(1))[0]).encode()
        if n == 1:
            return str(struct.unpack("<h", self.read(2))[0]).encode()
        if n == 2:
            return str(struct.unpack("<i", self.read(4))[0]).encode()
        if n == 3:
            compressed_len, _ = self.length()
            raw_len, _ = self.length()
            return _lzf_decompress(self.read(compressed_len), raw_len)
        raise RDBError(f"unknown string encoding {n}")


def _lzf_decompress(data, expected_len):
    out = bytearray()
    i = 0
    while i < len(data):
        ctrl = data[i]
        i += 1
        if ctrl < 32:  # literal run of ctrl + 1 bytes
            out += data[i:i + ctrl + 1]
            i += ctrl + 1
        else:  # back reference
            length = ctrl >> 5
            if length == 7:
                length += data[i]
                i += 1
            ref = len(out) - ((ctrl & 0x1F) << 8) - data[i] - 1
            i += 1
            for _ in range(length + 2):  # byte by byte: ranges may overlap
                out.append(out[ref])
                ref += 1
    if len(out) != expected_len:
        raise RDBError("LZF length mismatch")
    return bytes(out)


def _to_monotonic(unix_seconds):
    return time.monotonic() + (unix_seconds - time.time())


def parse(data):
    """Return {key: (value, expires_at or None)} with expires_at on the monotonic clock."""
    r = _Reader(data)
    if r.read(5) != b"REDIS":
        raise RDBError("missing REDIS magic")
    r.read(4)  # version, e.g. b"0011"

    entries = {}
    expires_unix = None
    while True:
        op = r.byte()
        if op == OP_EOF:
            break  # 8-byte checksum follows; not verified
        if op == OP_AUX:
            r.string()
            r.string()
        elif op == OP_SELECTDB:
            r.length()  # only db 0 is served; all dbs merge into one store
        elif op == OP_RESIZEDB:
            r.length()
            r.length()
        elif op == OP_EXPIRETIME_MS:
            expires_unix = struct.unpack("<Q", r.read(8))[0] / 1000
        elif op == OP_EXPIRETIME:
            expires_unix = struct.unpack("<I", r.read(4))[0]
        elif op == TYPE_STRING:
            key = r.string()
            value = r.string()
            if expires_unix is None:
                entries[key] = (value, None)
            elif expires_unix > time.time():
                entries[key] = (value, _to_monotonic(expires_unix))
            # else: already expired, skip
            expires_unix = None
        else:
            raise RDBError(f"unsupported value type or opcode {op:#x}")
    return entries


def load(config, store):
    """Fill `store` from config['dir']/config['dbfilename']. A missing file means an empty db."""
    path = os.path.join(config["dir"], config["dbfilename"])
    try:
        with open(path, "rb") as f:
            data = f.read()
    except FileNotFoundError:
        return 0
    entries = parse(data)
    store.update(entries)
    return len(entries)
