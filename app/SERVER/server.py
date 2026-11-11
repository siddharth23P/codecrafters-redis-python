"""Event-loop TCP server: reads requests, runs them, writes replies."""
import selectors
import socket

from .blocking import Blocked
from ..PROTOCOL.encoder import encode
from ..PROTOCOL.resp_types import ToMaster
from ..PROTOCOL.parser import Incomplete, ProtocolError, parse


class RedisServer:
    def __init__(self, address, dispatcher, blocking, tickers=(), tick_interval=0.1):
        self._address = address
        self._dispatcher = dispatcher        # request -> reply value
        self._blocking = blocking            # clients parked by BLPOP
        self._tickers = tickers              # objects with tick(), run every loop pass
        self._tick_interval = tick_interval  # max seconds select() sleeps
        self._sel = selectors.DefaultSelector()
        self._buffers: dict[socket.socket, bytes] = {}  # unparsed bytes per connection
        self._parked: set[socket.socket] = set()        # connections waiting in BLPOP
        self._silent: set[socket.socket] = set()        # master link: run commands, never reply

    def serve_forever(self):
        server = socket.create_server(self._address, reuse_port=True)
        server.setblocking(False)
        self._sel.register(server, selectors.EVENT_READ, self._accept)
        while True:
            for key, _ in self._sel.select(timeout=self._select_timeout()):
                key.data(key.fileobj)
            for ticker in self._tickers:
                ticker.tick()
            self._resume(self._blocking.timed_out())
            
    def attach_master(self, conn, leftover=b""):
        conn.setblocking(False)
        self._buffers[conn] = leftover
        self._silent.add(conn)
        self._sel.register(conn, selectors.EVENT_READ, self._read)
        self._run(conn)
    
    def _select_timeout(self):
        """Sleep until the next tick, or sooner if a BLPOP timeout is due."""
        due = self._blocking.next_timeout()
        return self._tick_interval if due is None else min(self._tick_interval, due)

    def _accept(self, server):
        conn, _ = server.accept()
        conn.setblocking(False)
        self._buffers[conn] = b""
        self._sel.register(conn, selectors.EVENT_READ, self._read)

    def _read(self, conn):
        try:
            data = conn.recv(1024)
        except OSError:
            data = b""
        if not data:
            self._close(conn)
            return
        self._buffers[conn] += data
        self._run(conn)

    def _run(self, conn, pending_reply=None):
        """Send pending_reply (if any), then run buffered requests until incomplete or blocked."""
        try:
            if pending_reply is not None:
                conn.sendall(encode(pending_reply))
            while conn not in self._parked:
                request, used = parse(self._buffers[conn])  # raises Incomplete when out of data
                self._buffers[conn] = self._buffers[conn][used:]
                reply = self._dispatcher.execute(conn, request)
                if isinstance(reply, Blocked):
                    self._parked.add(conn)
                    self._blocking.wait(conn, reply)
                elif conn not in self._silent or isinstance(reply, ToMaster):
                    conn.sendall(encode(reply))
                self._resume(self._blocking.served())  # this command may have fed a BLPOP client
        except Incomplete:
            pass
        except ProtocolError as e:
            conn.sendall(b"-ERR Protocol error: %s\r\n" % str(e).encode())
            self._close(conn)
        except Exception as e:  # one bad client must not stop the loop
            print(f"closing connection: {e!r}")
            self._close(conn)

    def _resume(self, replies):
        """Unpark each client, send its reply, and run whatever it queued while blocked."""
        for conn, reply in replies:
            self._parked.discard(conn)
            self._run(conn, pending_reply=reply)

    def _close(self, conn):
        if conn not in self._buffers:  # already closed
            return
        self._blocking.remove(conn)
        self._parked.discard(conn)
        del self._buffers[conn]
        self._sel.unregister(conn)
        self._dispatcher.forget(conn)
        self._silent.discard(conn)
        conn.close()
