import asyncio
import struct
from collections import defaultdict
import random
import bencode
import socket
import bitstring

CHUNK_SIZE = 2**14

class Peer(object):
    
    def __init__(self, torrent, host, port, pieces, file):
        self.host = host
        self.port = port
        self.torrent = torrent
        self.pieces = pieces

        self.choking = True
        self.interested = False

        self.broadcast = 0

        self.writer = None
        self.reader = None

        self.blocks =  None

        self.file = file

        self.have_pieces = bitstring.BitArray(
            bin='0' * self.torrent.number_of_pieces
        )

    
    @staticmethod
    def calculate_peer_id():
        id = '-PC0001-' + ''.join([str(random.randint(0, 9)) for _ in range(12)])
        return id.encode()

    async def send_interested(self, writer):   # Metodo que define el request para realizar el handshake con los peers
        msg = struct.pack('>Ib', 1, 2)
        writer.write(msg)
        await writer.drain()
    

    def get_handshake_params(self):            # Metodo que define el request para realizar el handshake con los peers
        return b''.join([
            chr(19).encode(),
            b'BitTorrent protocol',
            (chr(0) * 8).encode(),
            self.torrent.info_hash,
            self.calculate_peer_id(),
        ])

    @staticmethod
    def consume_data(buf, length):
        new_buf = buf[4:] 
        buf = new_buf[length:] 
        return buf
    
    @staticmethod
    def get_data(buf, length):
        return buf[:4 + length]


    async def handle_messages(self, buf_len, buf): # Gestionamiento de los mensajes recividos y enviados hacia cad uno del os peers intanciados
        
        msg_id = struct.unpack('>b', buf[4:5])[0]
        
        # Mensaje recivido Choke
        if msg_id == 0:
            print("Choke")
            data = self.get_data(buf, buf_len)
            buf = self.consume_data(buf, buf_len)
            self.choking = True

        
        # Mensaje recivido Unchoke
        elif msg_id == 1:
            print("Unchoke")
            data = self.get_data(buf, buf_len)
            buf = self.consume_data(buf, buf_len)
            self.broadcast = 1
            self.choking = False
        
        # Mensaje recivido Interested
        elif msg_id == 2:
            print("Interested")
            data = self.get_data(buf, buf_len)
            buf = self.consume_data(buf, buf_len)
            self.interested = True
            pass
        
        # Mensaje recivido Not Interested
        elif msg_id == 3:
            print("Not Interested")
            data = self.get_data(buf, buf_len)
            buf = self.consume_data(buf, buf_len)
            self.interested = False
            pass
        
        # Mensaje recivido Have
        elif msg_id == 4:
            print("Have")
            buf = buf[5:]
            data = self.get_data(buf, buf_len)
            buf = self.consume_data(buf, buf_len)
            pass
        
        # Mensaje recivido Bitfield
        elif msg_id == 5:
            print("Bitfield")
            bitfield = buf[5: 5 + buf_len - 1]
            self.have_pieces = bitstring.BitArray(bitfield)
            buf = buf[4 + buf_len:]
            await self.send_interested(self.writer)
        
        # Mensaje recivido Piece Request
        elif msg_id == 6:
            print("Piece Request")
            self.recv_piece_request()
        
        # Mensaje recivido Pieza Recibida
        elif msg_id == 7:
            print("Pieza Recibida")
            data = self.get_data(buf, buf_len)
            buf = self.consume_data(buf, buf_len)

            l = struct.unpack('>I', data[:4])[0]

            try:
                payload = struct.unpack(
                    '>IbII' + str(l - 9) + 's',
                    data[:buf_len + 4])
                piece_idx, begin, data = payload[2], payload[3], payload[4]
                await self.pieces.on_block_received(piece_idx, begin, data)

                self.broadcast = 1
                
            except struct.error:
                return None
        
        else:
            if msg_id == 159:
                exit(1)
        await self.request_a_piece()
        
        return buf
    
    async def send_have(self,index):

        try:
            data = struct.pack("IbI",5,4,index)
            self.writer.write(data)
            await self.write.drain()
            await self.reader.read()

        except:
            print("Error al enviar el have")
        
    
    def get_blocks_generator(self):
        def blocks():
            while True:
                piece = self.pieces.get_piece_request(self.have_pieces)
                for block in piece.blocks:
                    yield block
        if not self.blocks:
            self.blocks = blocks()
        return self.blocks

    async def recv_piece_request(self):
        payload = self.reader.read(CHUNK_SIZE)
        index, begin, size = struct.unpack(">III", payload)
        if (size > CHUNK_SIZE):
            print("Peer solicitado demasiada data")
        data = self.file.get_piece_by_index(self.torrent.number_of_pieces, index)
        self.writer.write(data) 
        await self.writer.drain()

    async def request_a_piece(self):

        blocks_generator = self.get_blocks_generator()
        block = next(blocks_generator)

        msg = struct.pack('>IbIII', 13, 6, block.piece_index, block.begin, block.length)
        self.writer.write(msg)
        await self.writer.drain()
    
    async def download(self):
        try:
            await self._download()
        except asyncio.TimeoutError:
            print("Tiempo de espera excedido al conectarse con el peer")

    async def _download(self):
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),  #conexion asyncio usando peer host y puerto      
                timeout=10
            )
        
        except Exception as e:
            print(e)
            return
        
        self.writer.write(self.get_handshake_params())

        await self.writer.drain()

        await self.reader.read(68)

        self.broadcast = 1
        
        await self.send_interested(self.writer)

        buf = b'' 

        while True:
            
            resp = await self.reader.read(CHUNK_SIZE)
            buf += resp

            if not buf and not resp:
                return
            
            while True:

                # if buf is None:
                #     break

                if len(buf) < 4:
                    break
                
                length = struct.unpack('>I', buf[0:4])[0]
                # print(struct.unpack('>I', buf[0:4]))
                # return
                if len(buf) <= length:
                    break

                if length == 0:
                    buf = self.consume_data(buf, length)
                    data = self.get_data(buf, length)
                    continue
                
                if len(buf) < 5:
                    break
                
                buf = await self.handle_messages(length, buf)