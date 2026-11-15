"""Replication: the master's view of its replicas, and the replica's handshake with its master."""
import socket

from ..PROTOCOL.encoder import encode
from .blocking import Blocked

WAIT_KEY = b"\x00wait"  # blocking key woken whenever a replica sends REPLCONF ACK


class Replicas:
    """Master side: connected replicas, the bytes sent to them, and the offsets they have acked."""

    def __init__(self, blocking):
        self._blocking = blocking
        self._conns = set()
        self._acked = {}   # replica conn -> last acked offset
        self._offset = 0   # bytes propagated so far

    def add(self, conn):
        self._conns.add(conn)

    def discard(self, conn):
        self._conns.discard(conn)
        self._acked.pop(conn, None)

    def ack(self, conn, offset):
        """Record REPLCONF ACK <offset> from a replica and wake WAIT clients."""
        self._acked[conn] = offset
        self._blocking.notify(WAIT_KEY)

    def propagate(self, request):
        data = encode(request)
        self._offset += len(data)
        for conn in list(self._conns):
            try:
                conn.sendall(data)
            except OSError:
                self.discard(conn)

    def wait(self, needed, timeout_ms):
        """WAIT numreplicas timeout: count of replicas that acked every write so far, or Blocked."""
        target = self._offset
        if target == 0:  # nothing written yet: every replica is in sync
            return len(self._conns)

        def in_sync():
            return sum(1 for conn in self._conns if self._acked.get(conn, 0) >= target)

        self.propagate([b"REPLCONF", b"GETACK", b"*"])
        return Blocked(
            keys=[WAIT_KEY],
            timeout=timeout_ms / 1000 if timeout_ms else None,
            serve=lambda _key: n if (n := in_sync()) >= needed else None,
            on_timeout=in_sync,
        )


def connect_to_master(replicaof, my_port):
    """Replica side: handshake with the master. Returns (socket, bytes received after the RDB)."""
    host, port = replicaof.split()
    conn = socket.create_connection((host, int(port)))
    buf = b""
    for cmd in ([b"PING"],
                [b"REPLCONF", b"listening-port", str(my_port).encode()],
                [b"REPLCONF", b"capa", b"psync2"],
                [b"PSYNC", b"?", b"-1"]):
        conn.sendall(encode(cmd))
        _, buf = _read_line(conn, buf)
    return conn, _skip_rdb(conn, buf)


def _recv(conn):
    data = conn.recv(1024)
    if not data:
        raise ConnectionError("master closed the connection during the handshake")
    return data


def _read_line(conn, buf):
    while b"\r\n" not in buf:
        buf += _recv(conn)
    line, _, rest = buf.partition(b"\r\n")
    return line, rest


def _skip_rdb(conn, buf):
    """Drop the RDB snapshot ($<len>\\r\\n<bytes>, no trailing CRLF); return the bytes after it."""
    header, buf = _read_line(conn, buf)
    size = int(header[1:])
    while len(buf) < size:
        buf += _recv(conn)
    return buf[size:]
