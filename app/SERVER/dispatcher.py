"""Route a parsed command to its handler. Knows nothing about sockets or RESP bytes."""
from typing import Any, Callable, Mapping

from ..PROTOCOL.resp_types import CommandError, ErrorReply

Command = Callable[[list], Any]  # args (list of bytes) -> reply value


class CommandDispatcher:
    def __init__(self, registry: Mapping[str, Command]):
        self._registry = registry  # name -> command, filled by COMMANDS.load

    def execute(self, request: Any) -> Any:
        """Run one request (e.g. [b'ECHO', b'hey']) and return its reply value."""
        if not isinstance(request, list) or not request or not isinstance(request[0], bytes):
            return ErrorReply("ERR Protocol error: expected an array of bulk strings")
        name = request[0].decode(errors="replace").lower()
        command = self._registry.get(name)
        if command is None:
            return ErrorReply(f"ERR unknown command '{name}'")
        try:
            return command(request[1:])
        except CommandError as e:
            return ErrorReply(f"{e.prefix} {e}")
