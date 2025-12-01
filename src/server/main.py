import socket
import threading
import json

class Server:
    def __init__(self, host="127.0.0.1", port=55555):
        self.host = host
        self.port = port
        # Do we use TCP or rather switch to UDP
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen()

        self.players = {}
        self.bombs = {}
        self.explosions = {}
        self.level_map = [[0, 0, 1, 0, 0],
                          [0, 0, 1, 0, 0],
                          [0, 0, 0, 0, 0],
                          [0, 0, 1, 0, 0],
                          [0, 0, 1, 0, 0]]

        self.player_map = [[1, 0, 0, 0, 0],
                           [0, 0, 0, 0, 0],
                           [0, 0, 0, 0, 0],
                           [0, 0, 0, 0, 0],
                           [0, 0, 0, 0, 0],]

        self.bomb_map = [[0, 0, 0, 0, 0],
                         [0, 0, 0, 0, 0],
                         [0, 0, 0, 0, 0],
                         [0, 0, 0, 0, 0],
                         [0, 0, 0, 0, 0],]

        self.Explosion_map = [[0, 0, 0, 0, 0],
                              [0, 0, 0, 0, 0],
                              [0, 0, 0, 0, 0],
                              [0, 0, 0, 0, 0],
                              [0, 0, 0, 0, 0],]
        #TODO multiple clients self.num_of_clients = 0
        #TODO multiple clients self.clients = {}

    """receives connection and starts a new thread for handling it"""
    def receive_connection(self):
        while True:
            client, address = self.server.accept()
            print("connected with ", address)
            #self.num_of_clients += 1
            thread = threading.Thread(target=self.handle, args=(client,))
            thread.start()

    """handles the connection"""
    def handle(self, client):
        self.send_board(client)
        # TODO waiting room self.waiting_room(client)
        while True:
            try:
                data = client.recv(1024).decode("utf-8")
                if not data:
                    break
                message = json.loads(data)
                self.handle_receive(message, client)
            except Exception as error:
                print("Couldn't handle", error)
                break
        # TODO client disconnecting

    """receives player actions from client and updates board"""
    def handle_receive(self, message, client):
        print(message)
        source = message.get("source")
        data = message.get("data")
        if data == "up" or data == "down" or data == "left" or data == "right":
            pass
            # TODO move player
        elif data == "bomb":
            pass
            # TODO update bomb map (&explosion map)
        self.send_board(client)

    """sends updated map to client"""
    def send_board(self, client):
        message = {"level_map": self.level_map, "player_map": self.player_map, "bomb_map": self.bomb_map, "explosion_map": self.Explosion_map}
        message = json.dumps(message).encode("utf-8")
        client.send(message)


if __name__ == "__main__":
    server = Server()
    server.receive_connection()