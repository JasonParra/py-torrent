from tracker import Tracker
from peer import Peer
from torrent import Torrent
from pieces import Pieces
from file import File
from upload import Upload
import asyncio
import struct
import socket
import bencode
import sys

CHUNK_SIZE = 2**14

#obtencion de file name por consola
args = sys.argv[1]

# Objeto encargado representar el torrent
torrent = Torrent(args)

# Objeto encargado de gestinar las escrituras y lecturas del disco 
torrent_writer = File('.', torrent)

async def download():

    print("Proceso de descarga inicializado. \n\nEs posible que se deba esperar un tiempo prologando para la obtencion de pieces para la descarga.\n")
    
    peer_addresses = await Tracker(torrent).begin_connection()
        
    # asignacion de la clase encargada de gestionar las piezas, como la descarga que sera utilizada por cada
    # valido para hacer la descarga 
            
    pieces = Pieces(torrent, torrent_writer.get_received_pieces_queue())
    
    # lista de peers intanciados con su parametro de torrent, puerto, host
    # y descarga previamente creada.

    peers = []

    for host, port in peer_addresses:
        peers.append(Peer(torrent, host, port, pieces, torrent_writer))

    # lista de ejecucion de la descarga realizada para cada peer, 
    # con su espera hasta que el mismo responda.

    for peer in peers:
        peer.pieces.peerList = peers
        await peer.download()
    
# hilo utilizado para la implementacion de upload totalemnte local
async def upload():

    print("Proceso upload inicializado")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 8000))
        s.listen(0)
        while True:
            conn, addr = s.accept()
            client = Upload(conn, addr,torrent)
            client.start()

loop = asyncio.get_event_loop()
task1 = loop.create_task(download())
# task2 = loop.create_task(upload())

try:
    loop.run_until_complete(task1)
    # loop.run_until_complete(task2)
    loop.close()
except Exception as e:
    print(e)
    raise(e)