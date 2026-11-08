"""Event-loop TCP server. Moves bytes between sockets and the request pipeline, nothing else."""
import selectors
import socket

from .blocking import Blocked
from .parser import Incomplete, ProtocolError


class RedisServer:
    def __init__(self, address, parser, dispatcher, encoder, blocking, selector=None,
                 tickers=(), tick_interval=0.1):
        self._address = address
        self._parser = parser          # bytes -> (request, bytes_used)
        self._dispatcher = dispatcher  # request -> reply value
        self._encoder = encoder        # reply value -> bytes
        self._blocking = blocking      # parks clients whose command returned Blocked
        self._sel = selector or selectors.DefaultSelector()
        self._tickers = tickers              # objects with tick(), run on every loop pass
        self._tick_interval = tick_interval  # max seconds select() sleeps, so tickers run when idle
        self._buffers: dict[socket.socket, bytes] = {}  # unparsed bytes per connection
        self._parked: dict[socket.socket, object] = {}  # conn -> Waiter, while blocked

    def serve_forever(self):
        server = socket.create_server(self._address, reuse_port=True)
        server.setblocking(False)
        self._sel.register(server, selectors.EVENT_READ, self._accept)
        while True:
            for key, _ in self._sel.select(timeout=self._select_timeout()):
                key.data(key.fileobj)
            for ticker in self._tickers:
                ticker.tick()

    def _select_timeout(self):
        """Sleep until the next tick, or sooner if a blocked client's timeout is due."""
        due = self._blocking.next_timeout()
        return self._tick_interval if due is None else min(self._tick_interval, due)

    def _accept(self, server):
        conn, _ = server.accept()
        conn.setblocking(False)
        self._buffers[conn] = b""
        self._sel.register(conn, selectors.EVENT_READ, self._handle)

    def _handle(self, conn):
        try:
            data = conn.recv(1024)
        except OSError:
            data = b""
        if not data:
            self._close(conn)
            return
        self._buffers[conn] += data
        if conn not in self._parked:  # a blocked client's commands wait until it is served
            self._guarded(conn, self._process)

    def _resume(self, conn, reply):
        """Called by the blocking registry when a parked client is served or times out."""
        self._parked.pop(conn, None)
        self._guarded(conn, lambda c: (c.sendall(self._encoder.encode(reply)), self._process(c)))

    def _guarded(self, conn, action):
        """Run action(conn); on failure close only this connection, never the loop."""
        try:
            action(conn)
        except ProtocolError as e:
            conn.sendall(b"-ERR Protocol error: %s\r\n" % str(e).encode())
            self._close(conn)
        except Exception as e:
            print(f"closing connection: {e!r}")
            self._close(conn)

    def _process(self, conn):
        """Run every complete request in the connection's buffer, until it blocks."""
        while self._buffers.get(conn) and conn not in self._parked:
            try:
                request, used = self._parser.parse(self._buffers[conn])
            except Incomplete:
                break
            self._buffers[conn] = self._buffers[conn][used:]
            reply = self._dispatcher.execute(request)
            if isinstance(reply, Blocked):
                self._parked[conn] = self._blocking.block(
                    reply, lambda r, c=conn: self._resume(c, r))
            else:
                conn.sendall(self._encoder.encode(reply))
            self._blocking.serve_ready()  # this command may have fed a waiting client

    def _close(self, conn):
        if conn not in self._buffers:  # already closed
            return
        waiter = self._parked.pop(conn, None)
        if waiter is not None:
            self._blocking.cancel(waiter)
        self._buffers.pop(conn, None)
        self._sel.unregister(conn)
        conn.close()
