"""Active expiry: frees expired keys that nobody reads again."""
import time


class ActiveExpirer:
    """Every `interval` seconds, delete expired keys from the store. Run from the event loop via tick()."""

    def __init__(self, store, interval=0.1):
        self._store = store        # key -> (value, expires_at or None)
        self._interval = interval  # seconds between sweeps
        self._next_run = 0.0

    def tick(self):
        now = time.monotonic()
        if now < self._next_run:
            return
        self._next_run = now + self._interval
        # collect first: deleting while iterating a dict raises RuntimeError
        expired = [key for key, (_, exp) in self._store.items() if exp is not None and exp <= now]
        for key in expired:
            del self._store[key]
