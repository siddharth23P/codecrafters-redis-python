from ..resp_types import CommandError


def run(args):
    """ECHO message -> message as a bulk string."""
    if len(args) != 1:
        raise CommandError("wrong number of arguments for 'echo' command")
    return args[0]
