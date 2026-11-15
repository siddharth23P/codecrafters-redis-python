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
    
    def opand(self, bitmap1: bytes, bitmap2: bytes) -> bytes:
        if bitmap1 is None or bitmap2 is None:
            return b""
        length = min(len(bitmap1), len(bitmap2))
        return bytes(b1 & b2 for b1, b2 in zip(bitmap1[:length], bitmap2[:length]))
    
    def opor(self, bitmap1: bytes, bitmap2: bytes) -> bytes:
        if bitmap1 is None:
            return bitmap2 or b""
        if bitmap2 is None:
            return bitmap1 or b""
        length = max(len(bitmap1), len(bitmap2))
        result = bytearray(length)
        for i in range(length):
            b1 = bitmap1[i] if i < len(bitmap1) else 0
            b2 = bitmap2[i] if i < len(bitmap2) else 0
            result[i] = b1 | b2
        return bytes(result)
    
    def opxor(self, bitmap1: bytes, bitmap2: bytes) -> bytes:
        if bitmap1 is None:
            return bitmap2 or b""
        if bitmap2 is None:
            return bitmap1 or b""
        length = max(len(bitmap1), len(bitmap2))
        result = bytearray(length)
        for i in range(length):
            b1 = bitmap1[i] if i < len(bitmap1) else 0
            b2 = bitmap2[i] if i < len(bitmap2) else 0
            result[i] = b1 ^ b2
        return bytes(result)
    
    def opnot(self, bitmap: bytes) -> bytes:
        if bitmap is None:
            return b""
        return bytes(~b & 0xFF for b in bitmap)