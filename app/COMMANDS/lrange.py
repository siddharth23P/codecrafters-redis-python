from ..resp_types import CommandError, ErrorReply, Array

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
        
        items = store[key][0]
        
        if not isinstance(items, list):
            return ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")
        
        stop = min(len(items)-1,stop)
        
        if start > stop:
            return Array([])
        
        return Array(items[start:stop+1])
        
        
    return run