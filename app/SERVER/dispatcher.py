"""Route a parsed command to its handler. Knows nothing about sockets or RESP bytes."""
from typing import Any, Callable, Mapping

from ..PROTOCOL.resp_types import CommandError, ErrorReply, SimpleString, Array

Command = Callable[[list], Any]  # args (list of bytes) -> reply value


class CommandDispatcher:
    def __init__(self, registry: Mapping[str, Command]):
        self._registry = registry  # name -> command, filled by COMMANDS.load
        self._transactions = {}

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
            return Array([self._run(r) for r in queue])
        
        if name == "discard":
            if queue is None:
                return ErrorReply("ERR DISCARD without MULTI")
            del self._transactions[conn]
            return SimpleString("OK")
        
        if name == "watch":
            return SimpleString("OK")
            
        if queue is not None:
            queue.append(request)
            return SimpleString("QUEUED")
        
        return self._run(request)
        
        
    def forget(self, conn):
        """Drop a closed connection's transaction."""
        self._transactions.pop(conn, None)
        
    def _run(self, request):
        name = request[0].decode(errors="replace").lower()
        command = self._registry.get(name)
        if command is None:
            return ErrorReply(f"ERR unknown command '{name}'")
        try:
            return command(request[1:])
        except CommandError as e:
            return ErrorReply(f"{e.prefix} {e}")
