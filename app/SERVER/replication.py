"""Replica side: connect to the master and do the handshake."""
import socket

from ..PROTOCOL.encoder import encode


def connect_to_master(replicaof, my_port, replication):
    """Handshake with master. Returns (socket, leftover bytes after the RDB)."""
    host, port = replicaof.split()
    conn = socket.create_connection((host, int(port)))
    buf = b""
    for cmd in ([b"PING"],
                [b"REPLCONF", b"listening-port", str(my_port)],
                [b"REPLCONF", b"capa", b"psync2"],
                [b"PSYNC", b"?", b"-1"]):
        conn.sendall(encode(cmd))
        _, buf = _read_line(conn, buf)
    leftover = _read_rdb(conn, buf)
    return conn, leftover

def _read_line(conn, buf):
    while b"\r\n" not in buf:
        buf += conn.recv(1024)
    line, _, rest = buf.partition(b"\r\n")
    return line, rest

def _read_rdb(conn, buf):
    header, buf = _read_line(conn, buf)          # b"$88"
    size = int(header[1:])
    while len(buf) < size:
        buf += conn.recv(1024)
    return buf[size:] 