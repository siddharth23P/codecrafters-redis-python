from ..PROTOCOL.resp_types import BulkString, WrongTypeError, CommandError, Integer
from . import check_arity, register, registered_commands, to_int
from ..DATASTRUCTURES.sortedsets import SortedSet

MIN_LATITUDE = -85.05112878
MAX_LATITUDE = 85.05112878
MIN_LONGITUDE = -180
MAX_LONGITUDE = 180

LATITUDE_RANGE = MAX_LATITUDE - MIN_LATITUDE
LONGITUDE_RANGE = MAX_LONGITUDE - MIN_LONGITUDE
        
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
            if entries.add(member, self._encoding_location_score(longitude, latitude)):
                added_count += 1
        return added_count
    
    @register
    def geopos(self, args):
        check_arity("geopos", len(args) >= 2)
        key, *members = args
        entries = self._get_sorted_set(key)
        if entries is None:
            return [None] * len(members)
        positions = []
        for member in members:
            score = entries.score(member)
            if score is None:
                positions.append(None)
            else:
                positions.append(self._decoding_location_score(score))
        return positions
    
    # --- helper methods for geospatial calculations ---
    @staticmethod
    def _validate_coordinates(longitude, latitude):
        if not (-180 <= longitude <= 180) or not (-85.05112878 <= latitude <= 85.05112878):
           return False
        return True
    
    @staticmethod
    def _interleave(x: int, y: int) -> int:
        """Interleave the bits of x and y. This is a helper for geospatial indexing."""
        x = GeoSpatialCommands._spread_int32_to_int64(x)
        y = GeoSpatialCommands._spread_int32_to_int64(y)
        y_shifted = y << 1
        return x | y_shifted
    
    @staticmethod
    def _deinterleave(grid_latitude_number: int, grid_longitude_number: int):
        """Deinterleave the bits of a Morton code to get the original x and y coordinates"""
        grid_latitude_min = MIN_LATITUDE + LATITUDE_RANGE * (grid_latitude_number / (2**26))
        grid_latitude_max = MIN_LATITUDE + LATITUDE_RANGE * ((grid_latitude_number + 1) / (2**26))
        grid_longitude_min = MIN_LONGITUDE + LONGITUDE_RANGE * (grid_longitude_number / (2**26))
        grid_longitude_max = MIN_LONGITUDE + LONGITUDE_RANGE * ((grid_longitude_number + 1) / (2**26))
        # Calculate the center point of the grid cell
        latitude = (grid_latitude_min + grid_latitude_max) / 2
        longitude = (grid_longitude_min + grid_longitude_max) / 2
        return (latitude, longitude)
    
    @staticmethod
    def _spread_int32_to_int64(v: int) -> int:
        """Spread a 32-bit integer into a 64-bit integer by interleaving its bits with zeros."""
        # Ensure only lower 32 bits are non-zero.
        v = v & 0xFFFFFFFF

        # Bitwise operations to spread 32 bits into 64 bits with zeros in-between
        v = (v | (v << 16)) & 0x0000FFFF0000FFFF
        v = (v | (v << 8))  & 0x00FF00FF00FF00FF
        v = (v | (v << 4))  & 0x0F0F0F0F0F0F0F0F
        v = (v | (v << 2))  & 0x3333333333333333
        v = (v | (v << 1))  & 0x5555555555555555

        return v
    
    @staticmethod
    def _compact_int64_to_int32(v: int) -> int:
        # Keep only the bits in even positions
        v = v & 0x5555555555555555
        # Before masking: w1   v1  ...   w2   v16  ... w31  v31  w32  v32
        # After masking: 0   v1  ...   0   v16  ... 0  v31  0  v32
        # Where w1, w2,..w31 are the digits from longitude if we're compacting latitude, or digits from latitude if we're compacting longitude
        # So, we mask them out and only keep the relevant bits that we wish to compact
        # ------
        # Reverse the spreading process by shifting and masking
        v = (v | (v >> 1)) & 0x3333333333333333
        v = (v | (v >> 2)) & 0x0F0F0F0F0F0F0F0F
        v = (v | (v >> 4)) & 0x00FF00FF00FF00FF
        v = (v | (v >> 8)) & 0x0000FFFF0000FFFF
        v = (v | (v >> 16)) & 0x00000000FFFFFFFF

        # Before compacting: 0   v1  ...   0   v16  ... 0  v31  0  v32
        # After compacting: v1  v2  ...  v31  v32
        # -----
        
        return v
    
    @staticmethod
    def _encoding_location_score(longitude, latitude):
        """Convert longitude and latitude to a score for the sorted set."""

        normalized_latitude = int(2**26 * (latitude - MIN_LATITUDE) / LATITUDE_RANGE)
        normalized_longitude = int(2**26 * (longitude - MIN_LONGITUDE) / LONGITUDE_RANGE)

        score = GeoSpatialCommands._interleave(normalized_latitude, normalized_longitude)
        return int(score)
    
    @staticmethod
    def _decoding_location_score(score):
        y = score >> 1
        x = score
        grid_latitude_number = GeoSpatialCommands._compact_int64_to_int32(x)
        grid_longitude_number = GeoSpatialCommands._compact_int64_to_int32(y)
        
        return GeoSpatialCommands._deinterleave(grid_latitude_number, grid_longitude_number)