from ..PROTOCOL.resp_types import CommandError, Integer, WrongTypeError
from . import check_arity, register, registered_commands, to_int
from ..DATASTRUCTURES.bitmaps import BitMaps

def create(ctx):
    return registered_commands(BitMapsCommands(ctx.store))


class BitMapsCommands:
    def __init__(self, store):
        self._store = store

    @register
    def setbit(self, args):
        check_arity("setbit", len(args) == 3)
        key, offset, value = args
        offset = to_int(offset)
        value = to_int(value)
        if value not in (0, 1) or offset < 0:
            raise CommandError("bit is not an integer or out of range")

        entry = self._store.get(key)
        if entry is None:
            bitmaps = BitMaps()
            self._store[key] = (bitmaps, None)
        else:
            bitmaps = entry[0]
            if not isinstance(bitmaps, BitMaps):
                raise WrongTypeError()
        
        oldbit = bitmaps.setbit(key, offset, value)
        return Integer(oldbit)
    
    @register
    def getbit(self, args):
        check_arity("getbit", len(args) == 2)
        key, offset = args
        offset = to_int(offset)
        if offset < 0:
            raise CommandError("bit offset is not an integer or out of range")

        entry = self._store.get(key)
        if entry is None:
            return Integer(0)
        
        bitmaps = entry[0]
        if not isinstance(bitmaps, BitMaps):
            raise WrongTypeError()
        
        bit = bitmaps.getbit(key, offset)
        return Integer(bit)