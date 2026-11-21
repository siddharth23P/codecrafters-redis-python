"""ACL: access-control subcommands (WHOAMI, ...)."""
from ..PROTOCOL.resp_types import BulkString, CommandError
from . import check_arity, register, registered_commands


def create(ctx):
    return registered_commands(ACL(ctx.store))


class ACL:
    def __init__(self, store):
        self._store = store

    @register
    def acl(self, args):
        """ACL <subcommand> [arg ...]"""
        check_arity("acl", len(args) >= 1)
        sub = args[0].lower()
        if sub == b"whoami":
            check_arity("acl|whoami", len(args) == 1)
            return BulkString(b"default")
        raise CommandError(f"Unknown ACL subcommand '{args[0].decode(errors='replace')}'")
