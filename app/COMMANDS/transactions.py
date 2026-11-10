"""Transaction commands."""
from . import check_arity, register, registered_commands, to_int
from ..PROTOCOL.resp_types import Array, BulkString, CommandError, Integer, SimpleString, WrongTypeError
from ..SERVER.blocking import Blocked
from collections import deque, OrderedDict
import time

def create(ctx):
    return registered_commands(TransactionCommands(ctx.store, ctx.blocking))

class TransactionCommands:
    def __init__(self, store, blocking):
        self._store = store
        self._blocking = blocking
        
    @register
    def incr(self,args):
        check_arity(args,"INCR",len(args) == 1)
        key = args[0]
        value, expires_at = self._store.get(key, (b"0", None))
        try:
            value = int(value) + 1
        except ValueError:
            raise CommandError("value is not an integer or out of range")
        self._store[key] = (str(value).encode(), expires_at)
        return Integer(value) 