import time
from ..resp_types import CommandError

def create(ctx):
    store = ctx.store

    def run(args):
        if len(args) != 1:
            raise CommandError("wrong number of arguments for 'get' command")
        entry = store.get(args[0])  # None encodes as $-1 (null)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and time.monotonic() >= expires_at:
            del store[args[0]]  # lazy expiry: remove on read
            return None
        return value
    return run
