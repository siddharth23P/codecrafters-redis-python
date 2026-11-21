"""ACL: access-control subcommands (WHOAMI, ...)."""
from ..PROTOCOL.resp_types import BulkString, SimpleString, Array, CommandError
from . import check_arity, register, registered_commands
import hashlib

def create(ctx):
    return registered_commands(ACL(ctx.store))

class ACL:
    def __init__(self, store):
        self._store = store
        # Users live here, not in the keyspace store, so they never show up in KEYS/DBSIZE.
        self._users = {
            b"default": {
                b"flags": [b"nopass"],
                b"passwords": [],
            }
        }

    @register
    def acl(self, args):
        """ACL <subcommand> [arg ...]"""
        check_arity("acl", len(args) >= 1)
        current_user = b"default"
        sub = args[0].lower()
        if sub == b"whoami":
            check_arity("acl|whoami", len(args) == 1)
            return BulkString(current_user)
        if sub == b"getuser":
            check_arity("acl|getuser", len(args) == 2)
            user = self._users.get(args[1])
            if user is None:
                return Array(None)
            return Array([b"flags", user[b"flags"], b"passwords", user[b"passwords"]])
        if sub == b"setuser":
            check_arity("acl|getuser", len(args) == 3)
            user = self._users.get(args[1])
            if user is None:
                return Array(None)
            password = args[2]
            hashed_password = hashlib.sha256(password[1:]).hexdigest()
            user[b"passwords"].append(hashed_password)
            return SimpleString("OK")
            
        raise CommandError(f"Unknown ACL subcommand '{args[0].decode(errors='replace')}'")
    
