from ..resp_types import CommandError, ErrorReply, Integer
from collections import deque
def create(ctx):
    store = ctx.store
    def run(args):
        if len(args) != 1:
            raise CommandError("wrong number of arguments for 'llen' command")
        key = args[0]

        if key not in store:
            return Integer(0)
        
        try:
            items = list(store[key][0])
        except TypeError:
            raise ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")
        
        n = len(items)
        
        return Integer(n)
        
    return run