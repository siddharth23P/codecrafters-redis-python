from ..resp_types import CommandError, ErrorReply, Integer

UNITS = {b"px": 1/1000, b"ex": 1}

def create(ctx):
    store = ctx.store

    def run(args):
        if len(args) < 2:
            raise CommandError("wrong number of arguments for 'rpush' command")
        key, *elements = args

        if key not in store:
            store[key] = [elements, None]
        else:
            items = store[key][0]
            if not isinstance(items, list):
                return ErrorReply("WRONGTYPE Operation against a key holding the wrong kind of value")
            items.extend(elements)
        return Integer(len(store[key][0]))

    return run