import sys
import bencode
import aiohttp
import random
from urllib.parse import urlencode,urlparse
import hashlib
import asyncio
import socket
from struct import unpack, pack, unpack_from
import ipaddress

class Tracker():
    def __init__(self, torrent):
        self.torrent_file = torrent
        self.request_type = 'http'
    
    def _calculate_peer_id(self):   #creacion arbitraria del peer_id tanto para http y udp
        if self.request_type == 'udp':
            return bytearray(b'-AZ2060-611784544578')
        else:
            return '-PC0001-' + ''.join([str(random.randint(0, 9)) for _ in range(12)])

    @staticmethod
    def _decode_port(port):          #decodificacion de puerto
        return unpack(">H", port)[0]
    
    def _parse_peers(self, peers):   #metodo para parseo de los peers y obtener la ip y puerto de la data recivida
        sliced_peers = []            
        parsed_peers = []
        
        for i in range(0, len(peers), 6):
            sliced_peers.append(peers[i:i+6])
        
        for p in sliced_peers:
            ip_address = socket.inet_ntoa(p[:4])
            port = self._decode_port(p[4:])
            parsed_peers.append((ip_address, port))

        return parsed_peers
    
    @staticmethod
    def parseAnnounce(url):         #parseo del announce para obtener el nombre host y el puerto
        parsed = urlparse(url)
        return parsed, parsed.hostname, parsed.port
    
    @staticmethod
    def decode_All(_response):
        response = unpack(">iiq",_response)
        return response

    @staticmethod
    def udp_create_connection_request():
        connection_id = 0x41727101980                   #id aleatorio de conexion
        action = 0x0                                    #action declarado en 0 para pedir el connection id  
        transaction_id = int(random.randrange(0, 10000))#transacion id generado aleatorio
        buf = pack("!q", connection_id)                 #primeros 8 bytes para el connection id
        buf += pack("!i", action)                       #los 4 bytes utilizados para el action
        buf += pack("!i", transaction_id)               #los 4 bytes utilizados para el transaction id
        return (buf, transaction_id)

    @staticmethod
    def get_peers(buf):                                 #metodo utilizado para parsear los peers
        peer_List=[]
        response = [buf[i:i+6] for i in range(20, len(buf), 6)]
        for peer in response:
            ip='.'.join(str(i) for i in peer[:4])
            port = int.from_bytes(peer[4:], byteorder='big')
            peer_List.append((ip, port))
        return peer_List

    @staticmethod
    def udp_create_announce_request(connection_id,transaction_id, payload, s_port):
        action = 0x1  # action declarado en 1 para ejecutar anncounce request
        transaction_id = transaction_id = int(random.randrange(0, 10000))
        buffer = pack("!q", connection_id)  # los primeros 8 bytes del connection id
        buffer += pack("!i", action)  # los 4 bytes del action
        buffer += pack("!i", transaction_id) #los 4 bytes del transacion id
        buffer += pack("!20s", payload['info_hash']) #el info hash del annouce que desaos realizar del torrent
        buffer += pack("!20s", payload['peer_id'])# el peer_id correspondiente al announce
        buffer += pack("!q", 0) #numero de bytes que se desan descargar
        buffer += pack("!q", 0) #numero de bytes restantes
        buffer += pack("!q", 0) #numero de bytes subidos
        buffer += pack("!i", 0x2) # evento 2 utilizado para destacar inicio de descarga
        buffer += pack("!i", 0x0)
        buffer += pack("!i", int(random.randrange(0, 10000)))  # llave unica generada por el cliente
        buffer += pack("!i", -1) #numero de peers requeridos, se inicializa en 1 por defecto
        buffer += pack("!H", s_port)  # puerto utilizado para recibir la  respuesta

        return (buffer, transaction_id)


    @staticmethod
    def get_connection_id(buf, sent_transaction_id):
        if len(buf) >= 16:

            action = unpack_from("!i", buf)[0]  # Se obtienen los primeros 4 bytes del action
            if action == 0x0:
                connection_id = unpack_from("!q", buf, 8)[0] # se desempacan los bytes para el connection_id
                return connection_id
            else:
                print("Error al conectarse")
                return None

    def announce_udp(self, tracker, payload):

        parsed, hostname, port = self.parseAnnounce(tracker) # se parse tracker url, pata obtener el parseao host y puerto

        ip = socket.gethostbyname(hostname) # obtencion de ip del hostname

        if ip == '127.0.0.1':   #Se retorna si la ip coincide con la local
            return

        # Se crea el socket, se instancia la conexion con el tracker, se envia 
        # el request del conexion y  se espera la respuesta del mismo
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(10)
        connection = (ip, port)
        req, transaction_id = self.udp_create_connection_request()
        sock.sendto(req, connection)
        sock.settimeout(10)
        buf = sock.recvfrom(2048)[0]
        self.decode_All(buf)

        # se genera el connection id con la informacion recivida del tracker 
        connection_id = self.get_connection_id(buf, transaction_id)
        s_port = sock.getsockname()[1]

        # con el connection id recivido se crea el annouce request para obtener los peers
        req, transaction_id = self.udp_create_announce_request(connection_id,transaction_id, payload, s_port)
        sock.sendto(req, connection)
        buf = sock.recvfrom(2048)[0] 

        return self.get_peers(buf)

    
    def get_params(self): #creacion de los parametros para realizar la peticion del announce al tracker
        return {
            'info_hash': self.torrent_file.info_hash,
            'peer_id': self._calculate_peer_id(),
            'port': 59696,
            'uploaded': 0,
            'downloaded': 0,
            'left': self.torrent_file.size,
            'compact': 1
        }


    # Metodo encargado de realizar la conexion http en caso de que el url del tracker sea http
    async def http_connect(self):
        params = self.get_params()

        url = self.torrent_file.announce_url + '?' + urlencode(params)
        
        async with aiohttp.ClientSession().get(url) as response:
            if not response.status == 200:
                raise ConnectionError('Error de conexion con tracker')
            data = await response.read()
            return self._parse_peers(bencode.decode(data)['peers'])


    # Metodo encargado de realizar un recorrido del annouce list del torrent file,
    # para luego tomar la decision si se debe relizar una conexionudp o http
    # para luego tomar la decision si se debe relizar una conexionudp o http
    async def begin_connection(self):
        
        for announce in self.torrent_file.announce_url_list:
            try:
                url = "".join(str(x) for x in announce)
                if 'udp' in url: 
                    self.request_type = 'udp'
                    params = self.get_params()
                    return self.announce_udp(url, params)
                else:
                    return await self.http_connect()
            except:
                print("Error al conectarse con el tracker")