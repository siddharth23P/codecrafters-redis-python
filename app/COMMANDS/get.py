from ..resp_types import CommandError

def create(ctx):
    store = ctx.store

    def run(args):
        if len(args) != 1:
            raise CommandError("wrong number of arguments for 'get' command")
        return store.get(args[0])  # None encodes as $-1 (null)

    return run
