import socket
import json

class ClientComms():
    def __init__(self, host="127.0.0.1", port=55555):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen()

    def receive_connection(self):
        client, address = self.server.accept()
        print("connected with ", address)
        #self.num_of_clients += 1
        return client

    def handle(self, client, queue):
        """Pushes the events to a queue"""
        while True:
            try:
                data = client.recv(1024).decode("utf-8")
                if not data:
                    break
                message = json.loads(data)
                queue.put(message)
            except Exception as error:
                print("Couldn't handle", error)
                break
        # TODO client disconnecting