from ..resp_types import CommandError, ErrorReply, Integer
from collections import deque

def create(ctx):
    store = ctx.store

    def run(args):
        if len(args) < 2:
            raise CommandError("wrong number of arguments for 'rpush' command")
        key, *elements = args

        if key not in store:
            store[key] = [deque(elements), None]
        else:
            items = store[key][0]
            if not isinstance(items, deque):
                return ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")
            items.extend(elements)
        return Integer(len(store[key][0]))

    return run