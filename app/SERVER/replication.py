"""Replica side: connect to the master and do the handshake."""
import socket

from ..PROTOCOL.encoder import encode


def connect_to_master(replicaof):
    """replicaof is "host port". Returns the open socket to the master."""
    host, port = replicaof.split()
    conn = socket.create_connection((host, int(port)))
    conn.sendall(encode([b"PING"]))
    conn.sendall(encode([b"REPLCONF",b"listening-port",str(port)]))
    conn.sendall(encode([b"REPLCONF",b"capa",b"psync2"]))
    return conn
