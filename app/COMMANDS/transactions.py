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
        if key not in self._store:
            self._store[key] = (Integer(1), None)
        try:
            value = int(self._store[key][0])
        except ValueError:
            raise CommandError("value is not an integer or out of range")
        self._store[key] = (Integer(value + 1), self._store[key][1])
        return self._store[key][0]
    