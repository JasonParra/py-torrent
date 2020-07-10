import hashlib
from pprint import pformat
import math
import bencode

class Torrent(object):
    def __init__(self, path):
        self.path = path
        self.info = self.read_torrent_file(path)

    @property
    def announce_url(self):                 #Propiedad en cargada de obtener el annouce del tracker principal del torrent seleccionado
        return self.info['announce']        

    @property
    def announce_url_list(self):            #Propiedad en cargada de obtener la lista de los urls de los trackers incluidos en el torrent file
        return self.info['announce-list']    

    @property
    def file_name(self):                    #Propiedad encargada de obtener el nombre del archivo solicitado
        return self.info['info']['name']

    @property
    def piece_length(self):                 #Propiedad utilizada para obtener la longitud de la pieza del torrent file
        return self.info['info']['piece length']

    @property
    def number_of_pieces(self):             #Propiedad utilizada para obtener el numero de piezas del torrent file
        return math.ceil(self.size / self.piece_length) 

    def get_piece_hash(self, piece_idx):    #Propiedad utilizada para obtener el hash de una pieza
        return self.info['info']['pieces'][piece_idx*20: (piece_idx*20) + 20]

    @property
    def info_hash(self):                     #Propiedad utilizada para obtener el hash info_hash encoded del torrent file
        return hashlib.sha1(bencode.encode(self.info['info'])).digest()

    @property                                #Propiedad utilizada para obtener la longitud del archivo
    def size(self):
        info = self.info['info']
        if 'length' in info:
            return int(info['length'])
        else:
            return sum([int(['length']) for f in info['files']])

    def read_torrent_file(self, path) -> dict: #Metodo utilizado para obtener una lectura del archivo
        with open(path, 'rb') as file:
            meta_info = file.read()
            torrent = bencode.decode(meta_info)
            return torrent