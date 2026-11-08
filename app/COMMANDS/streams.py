"""Stream commands."""
from . import check_arity, register, registered_commands, to_int
from ..PROTOCOL.resp_types import Array, BulkString, CommandError, Integer, SimpleString, WrongTypeError
from collections import deque, OrderedDict

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
        if isinstance(entry[0], OrderedDict):
            return SimpleString("stream")
        return SimpleString("string")
    
    @register
    def xadd(self,args):
        return self._push(args, "xadd")
        
    
    def _push(self,args,name):
        check_arity(args, name, len(args) >= 4 and len(args)%2 == 0)
        key, id, *kv_pairs = args
        if key not in self._store:
            kv_store = OrderedDict()
            self._store[key] = [kv_store, None]
        kv_store = self._store[key][0]
        
        ms, seq = map(int, id.split(b"-"))
        
        if (ms, seq) == (0, 0):
            raise CommandError("The ID specified in XADD must be greater than 0-0")
        
        last_id = next(reversed(kv_store), None)
        
        if last_id is not None and (ms, seq) <= tuple(map(int, last_id.split(b"-"))):
            raise CommandError("The ID specified in XADD is equal or smaller than the target stream top item")

        if id not in kv_store:
            kv_store[id] = dict()
            
        for index in range(len(kv_pairs)//2):
            key_index , value_index = index * 2 , (index * 2) + 1
            k = kv_pairs[key_index]
            v = kv_pairs[value_index]
            kv_store[id][k] = v
            
        return BulkString(id)
            
            
        
            
            
            
