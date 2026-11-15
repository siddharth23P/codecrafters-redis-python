class BitMaps:
    def __init__(self):
        self._bitmaps = {}

    def setbit(self, key: bytes, offset: int, value: int) -> int:
        if key not in self._bitmaps:
            self._bitmaps[key] = bytearray(1)
        bitmap = self._bitmaps[key]
        offset_byte, offset_bit = divmod(offset, 8)
        
        if offset_byte >= len(bitmap):
            missing_bytes = offset_byte + 1 - len(bitmap)
            bitmap.extend(bytearray(missing_bytes))
                
        if value not in (0, 1):
            raise ValueError("Value must be 0 or 1")
        
        oldbit = (bitmap[offset_byte] >> (7 - offset_bit)) & 1
        
        if value:
            bitmap[offset_byte] |= (1 << (7 - offset_bit))
        else:
            bitmap[offset_byte] &= ~(1 << (7 - offset_bit))
            
        return oldbit
            
        