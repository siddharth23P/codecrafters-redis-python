"""Connection commands: PING, ECHO."""
from . import check_arity, register, registered_commands
from ..PROTOCOL.resp_types import SimpleString


def create(ctx):
    return registered_commands(ConnectionCommands())


class ConnectionCommands:
    @register
    def ping(self, args):
        """PING -> +PONG.  PING message -> message as a bulk string."""
        check_arity(args, "ping", len(args) <= 1)
        return args[0] if args else SimpleString("PONG")

    @register
    def echo(self, args):
        """ECHO message -> message as a bulk string."""
        check_arity(args, "echo", len(args) == 1)
        return args[0]
