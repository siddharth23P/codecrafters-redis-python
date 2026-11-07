import time
from ..resp_types import CommandError, Integer

UNITS = {b"px": 1/1000, b"ex": 1}

def create(ctx):
    store = ctx.store

    def run(args):
        if len(args) not in (2,4):
            raise CommandError("wrong number of arguments for set command")
        key, *value = args
        expires_at = None
        # if option:
        #     unit, amount = option
        #     scale = UNITS.get(unit.lower())
        #     if scale is None or not amount.isdigit() or int(amount) == 0:
        #         raise CommandError("Syntax Error")
        #     expires_at = time.monotonic() + int(amount) * scale

        if key not in store:
        else:
            store[key][0].extend(value)
            store[key][1] = expires_at
        return Integer(len(store[key][0]))

    return run