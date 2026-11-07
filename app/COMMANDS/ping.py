from ..resp_types import CommandError, SimpleString


def run(args):
    """PING -> +PONG.  PING message -> message as a bulk string."""
    if not args:
        return SimpleString("PONG")
    if len(args) == 1:
        return args[0]
    raise CommandError("wrong number of arguments for 'ping' command")
