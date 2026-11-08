from ..resp_types import CommandError, ErrorReply, Array, BulkString
from collections import deque
def create(ctx):
    store = ctx.store
    def run(args):
        if len(args) not in [1,2]:
            raise CommandError("wrong number of arguments for 'lrange' command")
        key = args[0]
        pop = 1
        if len(args) == 2:
            try:
                pop = int(args[1])
            except ValueError:
                raise CommandError("value is not an integer or out of range")

        if key not in store:
            return Array([])
        
        try:
            items = list(store[key][0])
        except TypeError:
            raise ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")
        
        n = len(items)
        
        pop = min(pop,n)
        
        
        popped = []
        
        while (pop > 0):
            popped.append(store[key][0].popleft())
            pop -= 1
            
        if len(popped) == 0:
            return BulkString(None)
        elif len(popped) == 1:
            return BulkString(popped[0])
        return Array(popped)
        
        
    return run