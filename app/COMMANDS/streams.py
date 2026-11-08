"""Stream commands."""
from . import check_arity, register, registered_commands, to_int
from ..PROTOCOL.resp_types import Array, BulkString, CommandError, Integer, SimpleString, WrongTypeError
from collections import deque

def create(ctx):
    return registered_commands(StreamCommands(ctx.store))


class StreamCommands:
    def __init__(self, store):
        self._store = store
        
    @register
    def type(self,args):
        check_arity(args, "llen", len(args) == 1)
        key = args[0]
        entry = self._store.get(key)
        if entry is None:
            return SimpleString("none")
        if isinstance(entry[0], deque):
            return SimpleString("list")
        return SimpleString("string")
    
