class BitMaps:

    def setbit(self, bitmap: bytearray, offset: int, value: int) -> int:
        offset_byte, offset_bit = divmod(offset, 8)

        if offset_byte >= len(bitmap):
            missing_bytes = offset_byte + 1 - len(bitmap)
            bitmap.extend(bytearray(missing_bytes))

        if value not in (0, 1):
            raise ValueError("Value must be 0 or 1")

        oldbit = self.getbit(bitmap, offset)

        if value:
            bitmap[offset_byte] |= (1 << (7 - offset_bit))
        else:
            bitmap[offset_byte] &= ~(1 << (7 - offset_bit))

        return oldbit

    def getbit(self, bitmap: bytes, offset: int) -> int:
        if bitmap is None:
            return 0

        offset_byte, offset_bit = divmod(offset, 8)

        if offset_byte >= len(bitmap):
            return 0

        return (bitmap[offset_byte] >> (7 - offset_bit)) & 1
    
    def count(self, bitmap: bytes) -> int:
        if bitmap is None:
            return 0
        return sum(bin(byte).count("1") for byte in bitmap)