import bitstring
import hashlib

class Piece(object):
    def __init__(self, piece_index, blocks):
        self.index = piece_index
        self.blocks = blocks
        self.downloaded_blocks : bitstring.BitArray = bitstring.BitArray(bin='0'*len(blocks))

    def flush(self):
        for block in self.blocks:
            block.flush()

    def is_complete(self) -> bool:
        return all(self.downloaded_blocks)

    def save_block(self, begin, data):
        for block_idx, block in enumerate(self.blocks):
            if block.begin == begin:
                block.data = data
                self.downloaded_blocks[block_idx] = True

    @property
    def data(self) -> bytes:
        return b''.join([block.data for block in self.blocks])

    @property
    def hash(self):
        return hashlib.sha1(self.data)
