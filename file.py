import asyncio
import os

class File(object):
    def __init__(self, outdir, torrent):
        self.torrent_file = torrent
        self.file_name = self.get_file_path(outdir, torrent)
        self.fd = os.open(self.file_name, os.O_RDWR | os.O_CREAT)
        self.received_pieces_queue = asyncio.Queue()
        asyncio.ensure_future(self.start())

    def get_received_pieces_queue(self):
        print('Pieza Recibida')
        return self.received_pieces_queue

    def get_file_path(self, outdir, torrent):
        name = torrent.file_name
        file_path = os.path.join(outdir, name)
        return file_path
    
    def get_piece_by_index(self, piece_index):
        with open(self.torrent_file.file_name, "rb") as f:
            for piece in range(self.torrent_file.number_of_pieces):
                data = (f.read(self.torrent_file.piece_length))
                if(piece == piece_index):
                    break
        return data
            
    async def start(self):
        while True:
            piece = await self.received_pieces_queue.get()
            if not piece:
                print('La pieza no existe')

            print("guardando pieza en el disco")
            piece_abs_location, pieces_data = piece
            os.lseek(self.fd, piece_abs_location, os.SEEK_SET)
            os.write(self.fd, pieces_data)