import socket
import json

class ServerComms():

    def __init__(self, host="127.0.0.1", port=55555):
        self.host = host
        self.port = port
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        
    def send_event(self, event_type, data):
        message = {"event_type": event_type, "data": data}
        message = json.dumps(message).encode("utf-8")
        self.sock.send(message)