"""Route a parsed command to its handler. Knows nothing about sockets or RESP bytes."""
from typing import Any, Callable, Mapping
from ..PROTOCOL.encoder import encode
from ..PROTOCOL.resp_types import CommandError, ErrorReply, SimpleString, Array

Command = Callable[[list], Any]  # args (list of bytes) -> reply value

WRITE_COMMANDS = {"set", "incr", "rpush", "lpush", "lpop", "blpop", "xadd"}

class CommandDispatcher:
    def __init__(self, registry: Mapping[str, Command]):
        self._registry = registry  # name -> command, filled by COMMANDS.load
        self._transactions = {}
        self._watching = {}
        self._dirty = set()
        self._replicas = set()

    def execute(self,conn, request: Any) -> Any:
        """Run one request (e.g. [b'ECHO', b'hey']) and return its reply value."""
        if not isinstance(request, list) or not request or not isinstance(request[0], bytes):
            return ErrorReply("ERR Protocol error: expected an array of bulk strings")
        name = request[0].decode(errors="replace").lower()
        queue = self._transactions.get(conn)
        
        if name == "multi":
            if queue is not None:
                return ErrorReply("ERR MULTI calls can not be nested")
            self._transactions[conn] = []
            return SimpleString("OK")
        
        if name == "exec":
            if queue is None:
                return ErrorReply("ERR EXEC without MULTI")
            del self._transactions[conn]
            aborted = conn in self._dirty
            self._unwatch(conn)
            if aborted:
                return Array(None)
            return Array([self._run(r) for r in queue])
        
        if name == "discard":
            if queue is None:
                return ErrorReply("ERR DISCARD without MULTI")
            del self._transactions[conn]
            self._unwatch(conn)
            return SimpleString("OK")
        
        if name == "watch":
            if queue is not None:
                return ErrorReply("ERR WATCH inside MULTI is not allowed")
            for key in request[1:]:
                self._watching.setdefault(key, set()).add(conn)
            return SimpleString("OK")
        
        if name == "unwatch":
            self._unwatch(conn)
            return SimpleString("OK")
        
        if queue is not None:
            queue.append(request)
            return SimpleString("QUEUED")
        
        reply = self._run(request)
        if name == "psync" and not isinstance(reply, ErrorReply):
            self._replicas.add(conn)
        return reply
        
        
    def forget(self, conn):
        """Drop a closed connection's transaction."""
        self._transactions.pop(conn, None)
        self._unwatch(conn)
        self._replicas.discard(conn)
        
    def _unwatch(self,conn):
        self._dirty.discard(conn)
        for watchers in self._watching.values():
            watchers.discard(conn)
        
    def _run(self, request):
        name = request[0].decode(errors="replace").lower()
        command = self._registry.get(name)
        if command is None:
            return ErrorReply(f"ERR unknown command '{name}'")
        try:
            reply = command(request[1:])
        except CommandError as e:
            return ErrorReply(f"{e.prefix} {e}")
        
        if name in WRITE_COMMANDS and len(request) > 1:
            self._dirty.update(self._watching.get(request[1],()))
            self._propagate(request)
        return reply
    
    def _propagate(self, request):
        data = encode(request)
        for replica in list(self._replicas):
            try:
                replica.sendall(data)
            except OSError:
                self._replicas.discard(replica)
        
        
