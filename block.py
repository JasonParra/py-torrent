class Block(object):
    def __init__(self, piece, begin, length):
        self.piece_index = piece
        self.begin = begin
        self.length = length
        self.data = None

    def flush(self):
        self.data = None
