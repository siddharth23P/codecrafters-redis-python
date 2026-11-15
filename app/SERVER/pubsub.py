"""Replication: the master's view of its replicas, and the replica's handshake with its master."""
import socket

from ..PROTOCOL.encoder import encode
from .blocking import Blocked

class PUBSUB:
    """Master side: connected replicas, the bytes sent to them, and the offsets they have acked."""

    def __init__(self):
        self._subscribers = {}
        self._channels = {}
        
    def subscribe(self, conn, channels):
        mine = self._channels.setdefault(conn, set())
        replies = []
        for channel in channels:
            mine.add(channel)
            self._subscribers.setdefault(channel, set()).add(conn)
            replies.append([b"subscribe", channel, len(mine)])
        return replies
    