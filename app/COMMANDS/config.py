"""CONFIG GET: read the server's startup parameters (dir, dbfilename, appendonly, ...)."""
from ..PROTOCOL.resp_types import Array, CommandError
from . import check_arity, register, registered_commands


def create(ctx):
    return registered_commands(ConfigCommands(ctx.config))


class ConfigCommands:
    def __init__(self, config):
        self._config = config  # parameter name -> str value

    @register
    def config(self, args):
        """CONFIG GET parameter [parameter ...] -> [name, value, ...] for each known parameter"""
        check_arity("config", len(args) >= 1)
        if args[0].lower() != b"get":
            raise CommandError(f"Unknown CONFIG subcommand '{args[0].decode(errors='replace')}'")
        check_arity("config|get", len(args) >= 2)
        wanted = {arg.decode(errors="replace").lower() for arg in args[1:]}
        reply = []
        for name, value in self._config.items():
            if name in wanted:
                reply += [name.encode(), value.encode()]
        return Array(reply)
