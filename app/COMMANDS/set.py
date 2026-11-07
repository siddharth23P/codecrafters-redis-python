from ..resp_types import CommandError, SimpleString

def create(ctx):
    store = ctx.store
    
    def run(args):
        if len(args) != 2:
            raise CommandError("wrong number of arguments for set command")
        key, value = args
        store[key] = value
        return SimpleString("OK")
    
    return run