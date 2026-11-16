from ..PROTOCOL.resp_types import BulkString, WrongTypeError, CommandError, Integer
from . import check_arity, register, registered_commands, to_int
from ..DATASTRUCTURES.sortedsets import SortedSet

def create(ctx):
    return registered_commands(GeoSpatialCommands(ctx.store))

class GeoSpatialCommands:
    def __init__(self, store):
        self._store = store

    def _get_sorted_set(self, key):
        """Return the SortedSet at key, or None. Store entries are [value, expires_at]."""
        entry = self._store.get(key)
        if entry is None:
            return None
        if not isinstance(entry[0], SortedSet):
            raise WrongTypeError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return entry[0]

    def _init_sorted_set(self, key):
        entries = self._get_sorted_set(key)
        if entries is None:
            entries = SortedSet()
            self._store[key] = [entries, None]
        return entries
    
    @register
    def geoadd(self, args):
        check_arity("geoadd", len(args) >= 4 and len(args) % 3 == 1)
        key, *triplets = args
        entries = self._init_sorted_set(key)
        added_count = 0
        for i in range(0, len(triplets), 3):
            longitude = float(triplets[i])
            latitude = float(triplets[i + 1])
            if not self._validate_coordinates(longitude, latitude):
                raise CommandError(f"ERR invalid longitude, latitude pair ({longitude}, {latitude})")
            member = triplets[i + 2]
            if entries.add(member, (longitude, latitude)):
                added_count += 1
        return added_count
    
    # --- helper methods for geospatial calculations ---
    def _validate_coordinates(self, longitude, latitude):
        if not (-180 <= longitude <= 180) or not (-85.05112878 <= latitude <= 85.05112878):
           return False
        return True