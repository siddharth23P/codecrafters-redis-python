"""Route a parsed command to its handler. Knows nothing about sockets or RESP bytes.

Handles the commands that depend on the calling connection (transactions, WATCH, WAIT,
REPLCONF ACK) itself; everything else goes to the command registry.
"""
from typing import Any, Callable, Mapping

from ..PROTOCOL.encoder import encode
from ..PROTOCOL.resp_types import Array, CommandError, ErrorReply, Integer, NoReply, Raw, SimpleString

Command = Callable[[list], Any]  # args (list of bytes) -> reply value

# Commands that change the store: logged to the AOF, propagated to replicas, and dirty WATCHed keys.
WRITE_COMMANDS = {"set", "incr", "rpush", "lpush", "lpop", "blpop", "xadd"}
SUBSCRIBED_MODE_ALLOWED = {"subscribe", "unsubscribe", "psubscribe", "punsubscribe", "ping", "quit", "reset"}

OK = SimpleString("OK")


def _name(request) -> str:
    return request[0].decode(errors="replace").lower()


class CommandDispatcher:
    def __init__(self, registry: Mapping[str, Command], replicas, aof, pubsubs):
        self._registry = registry  # name -> command, filled by COMMANDS.load
        self._replicas = replicas  # replication.Replicas
        self._pubsub = pubsubs     # pubsub.PUBSUB
        self._aof = aof            # aof.Appender
        self._transactions = {}    # conn -> queued requests, while inside MULTI
        self._watching = {}        # key -> conns watching it
        self._dirty = set()        # conns whose watched keys changed; their EXEC aborts
        self._per_connection = {
            "multi": self._multi,
            "exec": self._exec,
            "discard": self._discard,
            "watch": self._watch,
            "unwatch": self._unwatch_command,
            "wait": self._wait,
            "subscribe": self._subscribe,
            "publish": self._publish,
        }

    def execute(self, conn, request: Any) -> Any:
        """Run one request (e.g. [b'ECHO', b'hey']) for conn and return its reply value."""
        if not isinstance(request, list) or not request or not isinstance(request[0], bytes):
            return ErrorReply("ERR Protocol error: expected an array of bulk strings")
        name = _name(request)

        if name == "replconf" and len(request) >= 3 and request[1].lower() == b"ack":
            self._replicas.ack(conn, int(request[2]))
            return NoReply()
        
        if self._pubsub.is_subscribed(conn):
            if name not in SUBSCRIBED_MODE_ALLOWED:
                return ErrorReply(f"ERR Can't execute '{name}': only (P|S)SUBSCRIBE / (P|S)UNSUBSCRIBE / PING / QUIT / RESET are allowed in this context")

            if name == "ping":
                return Array([b"pong", request[1] if len(request) > 1 else b""])
        
        handler = self._per_connection.get(name)
        if handler is not None:
            return handler(conn, request[1:])

        queue = self._transactions.get(conn)
        if queue is not None:
            queue.append(request)
            return SimpleString("QUEUED")

        reply = self._run(request)
        if name == "psync" and not isinstance(reply, ErrorReply):
            self._replicas.add(conn)
        return reply

    def forget(self, conn):
        """Drop all state for a closed connection."""
        self._transactions.pop(conn, None)
        self._unwatch(conn)
        self._replicas.discard(conn)
        self._pubsub.forget(conn)

    # --- per-connection commands ---

    def _multi(self, conn, _args):
        if conn in self._transactions:
            return ErrorReply("ERR MULTI calls can not be nested")
        self._transactions[conn] = []
        return OK
    
    def _subscribe(self, conn, channels):
        replies = self._pubsub.subscribe(conn, channels)
        return Raw(b"".join(encode(r) for r in replies))
    
    def _publish(self, _conn, args):
        if len(args) != 2:
            return ErrorReply("ERR wrong number of arguments for 'publish' command")
        channel, message = args
        self._pubsub.publish(channel, message)
        return Integer(len(self._pubsub._subscribers.get(channel, set())))

    def _exec(self, conn, _args):
        queue = self._transactions.pop(conn, None)
        if queue is None:
            return ErrorReply("ERR EXEC without MULTI")
        aborted = conn in self._dirty
        self._unwatch(conn)
        return Array(None) if aborted else Array([self._run(r) for r in queue])

    def _discard(self, conn, _args):
        if self._transactions.pop(conn, None) is None:
            return ErrorReply("ERR DISCARD without MULTI")
        self._unwatch(conn)
        return OK

    def _watch(self, conn, keys):
        if conn in self._transactions:
            return ErrorReply("ERR WATCH inside MULTI is not allowed")
        for key in keys:
            self._watching.setdefault(key, set()).add(conn)
        return OK

    def _unwatch_command(self, conn, _args):
        self._unwatch(conn)
        return OK

    def _wait(self, _conn, args):
        if len(args) != 2:
            return ErrorReply("ERR wrong number of arguments for 'wait' command")
        try:
            needed, timeout_ms = int(args[0]), int(args[1])
        except ValueError:
            return ErrorReply("ERR value is not an integer or out of range")
        return self._replicas.wait(needed, timeout_ms)

    # --- helpers ---

    def _unwatch(self, conn):
        self._dirty.discard(conn)
        for watchers in self._watching.values():
            watchers.discard(conn)

    def _run(self, request):
        """Run a registry command; on a write, log it, dirty its watchers and send it to replicas."""
        name = _name(request)
        command = self._registry.get(name)
        if command is None:
            return ErrorReply(f"ERR unknown command '{name}'")
        try:
            reply = command(request[1:])
        except CommandError as e:
            return ErrorReply(f"{e.prefix} {e}")

        if name in WRITE_COMMANDS and len(request) > 1:
            self._aof.append(request)
            self._dirty.update(self._watching.get(request[1], ()))
            self._replicas.propagate(request)
        return reply
