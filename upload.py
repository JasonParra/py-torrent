import threading
import pickle
import random
import socket
import struct

class Upload(threading.Thread):
    def __init__(self, conn, addr, torrent):
        threading.Thread.__init__(self)
        self.conn = conn
        self.addr = addr    
        self.torrent = torrent
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def run(self):
        with self.conn:
            #haciendo handshake
            try:
                print('New ip has joined: ', self.addr)
                payload = self.get_handshake_params()
                self.sock.connect(self.addr)
                self.sock.send(payload)
                self.sock.timeout(10)
                response = self.sock.recvfrom(2048)
                self.verify_handshake(response, payload)
            except:
                print("Error de handshake")
            
            # #mandado bitfield
            # try:
            #      
            # except:
            #     print("Error mandando bitfield")

                    
    def calculate_peer_id(self):
        id = '-PC0001-' + ''.join([str(random.randint(0, 9)) for _ in range(12)])
        return id.encode()

    def get_handshake_params(self):            # Metodo que define el request para realizar el handshake con los peers
        return b''.join([
            chr(19).encode(),
            b'BitTorrent protocol',
            (chr(0) * 8).encode(),
            self.torrent.info_hash,
            self.calculate_peer_id(),
        ])     

    def verify_handshake(self,response, payload):
        total =0
        if (len(response)> 28): 
            for i in range(28, 48, 1):
                if (payload[i]==response[i]):
                    total=total+1
                if(total == 20):
                    print("Handshake correcto")
                    return True
    



    


    
