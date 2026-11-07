"""Event-loop TCP server. Moves bytes between sockets and the request pipeline, nothing else."""
import selectors
import socket

from .parser import Incomplete, ProtocolError


class RedisServer:
    def __init__(self, address, parser, dispatcher, encoder, selector=None):
        self._address = address
        self._parser = parser          # bytes -> (request, bytes_used)
        self._dispatcher = dispatcher  # request -> reply value
        self._encoder = encoder        # reply value -> bytes
        self._sel = selector or selectors.DefaultSelector()
        self._buffers: dict[socket.socket, bytes] = {}  # unparsed bytes per connection

    def serve_forever(self):
        server = socket.create_server(self._address, reuse_port=True)
        server.setblocking(False)
        self._sel.register(server, selectors.EVENT_READ, self._accept)
        while True:
            for key, _ in self._sel.select():
                key.data(key.fileobj)

    def _accept(self, server):
        conn, _ = server.accept()
        conn.setblocking(False)
        self._buffers[conn] = b""
        self._sel.register(conn, selectors.EVENT_READ, self._handle)

    def _handle(self, conn):
        try:
            data = conn.recv(1024)
            if not data:
                self._close(conn)
                return
            self._buffers[conn] = self._process(conn, self._buffers[conn] + data)
        except ProtocolError as e:
            conn.sendall(b"-ERR Protocol error: %s\r\n" % str(e).encode())
            self._close(conn)
        except Exception as e:  # one bad client must not stop the single-threaded loop
            print(f"closing {conn.getpeername()}: {e!r}")
            self._close(conn)

    def _process(self, conn, buf):
        """Run every complete request in buf. Return the leftover partial bytes."""
        while buf:
            try:
                request, used = self._parser.parse(buf)
            except Incomplete:
                break
            buf = buf[used:]
            reply = self._dispatcher.execute(request)
            conn.sendall(self._encoder.encode(reply))
        return buf

    def _close(self, conn):
        self._buffers.pop(conn, None)
        self._sel.unregister(conn)
        conn.close()
