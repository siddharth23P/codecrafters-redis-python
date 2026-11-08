from ..resp_types import CommandError, ErrorReply, Array
from collections import deque
def create(ctx):
    store = ctx.store
    def run(args):
        if len(args) != 3:
            raise CommandError("wrong number of arguments for 'lrange' command")
        key = args[0]
        try:
            start, stop = int(args[1]), int(args[2])
        except ValueError:
            raise CommandError("value is not an integer or out of range")

        if key not in store:
            return Array([])
        
        try:
            items = list(store[key][0])
        except TypeError:
            raise ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")
        
        n = len(items)
        
        if start < 0:
            start = max(n + start, 0)
        if stop < 0:
            stop = n + stop
        stop = min(stop, n - 1)
        
        if start > stop:
            return Array([])
        
        return Array(items[start:stop+1])
        
        
    return run