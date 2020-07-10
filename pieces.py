import asyncio
import bitstring
import hashlib
import math
import sys
from block import Block
from piece import Piece
from pprint import pformat
import bencode
import socket
from torrent import Torrent
from tracker import Tracker
import struct

class Pieces(object):
    def __init__(self, torrent, received_blocks):
        self.torrent : Torrent = torrent
        self.piece_size = self.torrent.piece_length
        self.number_of_pieces = self.torrent.number_of_pieces
        self.pieces = self.get_pieces()
        self.pieces_in_progress : Dict[int, Piece] = {}
        self.received_pieces : Dict[int, Piece]= {}
        self.received_blocks : asyncio.Queue = received_blocks
        self.peerList = []

    async def on_block_received(self, piece_idx, begin, data):

        piece = self.pieces[piece_idx]
        piece.save_block(begin, data)

        if not piece.is_complete():
            return

        piece_data = piece.data

        # Comparacrion de hash entre el recivido y el esperado
        res_hash = hashlib.sha1(piece_data).digest()
        exp_hash = self.torrent.get_piece_hash(piece.index)     
        if res_hash != exp_hash:
            piece.flush()
            return

        self.received_blocks.put_nowait((piece.index * self.piece_size, piece_data))
        await self.send_broadcast_have(piece.index)

    async def send_broadcast_have(self,index):
        broadcast_value = 0
        try:
            i = 0
            for peer in self.peerList:
                if (peer.broadcast == broadcast_value):
                    i+=1

            print("cantidad de peers disponibles para seeding: " + str(i))
            
            for peer in self.peerList:
                if (peer.broadcast == broadcast_value):
                    await peer.send_have(index)
            
        except:
            print("fallo de envio mensaje have\n")


    def get_pieces(self) -> list:
        pieces = []                             # buffer para almacenar piezas
        CHUNK_SIZE = 2**14
        blocks_per_piece = math.ceil(self.piece_size / CHUNK_SIZE)
        for piece_idx in range(self.number_of_pieces):
            blocks = []                          # buffer para almacenar bloques
            for block_idx in range(blocks_per_piece):
                is_last_block = (blocks_per_piece - 1) == block_idx
                if is_last_block:
                    block_length = (self.piece_size % CHUNK_SIZE) or CHUNK_SIZE #
                else:
                    block_length = CHUNK_SIZE
                blocks.append(
                    Block(
                        piece_idx,                # indice de la pieza
                        block_length * block_idx, # principio de la pieza 
                        block_length              # tamano de la pieza 
                    )
                )
            pieces.append(Piece(piece_idx, blocks))
        return pieces

    def get_piece_request(self, have_pieces):
        for piece in self.pieces:
            is_piece_downloaded = piece.index in self.received_pieces
            is_piece_in_progress = piece.index in self.pieces_in_progress

            if is_piece_downloaded or is_piece_in_progress:   #saltar pieza si ya la poseemos
                continue

            if have_pieces[piece.index]:
                self.pieces_in_progress[piece.index] = piece
                return piece
        raise Exception('piece no valida')
