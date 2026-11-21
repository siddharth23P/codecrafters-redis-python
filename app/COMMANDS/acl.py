"""ACL: access-control subcommands (WHOAMI, ...)."""
from ..PROTOCOL.resp_types import BulkString,Array, CommandError
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
        user = self._store.get("users",{b"default":[b"nopass"]})
        current_user = b"default"
        sub = args[0].lower()
        if sub == b"whoami":
            check_arity("acl|whoami", len(args) == 1)
            return BulkString(current_user)
        if sub == b"getuser":
            check_arity("acl|whoami", len(args) in [1,2])
            guser_name = b"default"
            if len(args) == 2:
                guser_name = args[1].lower()
            return Array(["flags",Array(user.get(guser_name,[]))])
            
        raise CommandError(f"Unknown ACL subcommand '{args[0].decode(errors='replace')}'")
