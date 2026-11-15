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
    
    def is_subscribed(self, conn):
        return conn in self._channels
    
    def publish(self, channel, message):
        for conn in self._subscribers.get(channel, set()):
            conn.send(encode([b"message", channel, message]))
    
    def forget(self, conn):
        """Drop all state for a closed connection."""
        channels = self._channels.pop(conn, set())
        for channel in channels:
            self._subscribers[channel].discard(conn)
            if not self._subscribers[channel]:
                del self._subscribers[channel]
    