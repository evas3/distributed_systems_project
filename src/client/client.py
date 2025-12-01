import socket
import threading
import json


class Client:
    def __init__(self, host="127.0.0.1", port=55555):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.connect((host, port))  
        self.closed = False

    """new thread to handle receiving data"""
    def start(self):
        receive_thread = threading.Thread(target=self.receive)
        receive_thread.start()

    """receive data from server"""
    def receive(self):
        while not self.closed:
            try:
                data = self.server.recv(1024).decode("utf-8")
                message = json.loads(data)
                print(message)
                #self.handle_response(message)
            except Exception as error:
                print("Error receiving data:", error)
                break
        self.close()

    """send data to server"""
    def send(self, message, id):
        data = {"source": id, "data": message}
        self.server.send(json.dumps(data).encode("utf-8"))

    """close connection"""
    def close(self):
        self.closed = True
        self.server.close()