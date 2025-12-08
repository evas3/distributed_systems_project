import socket
import json

class ClientComms():
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server = None
        self.acks = 0

    def start_listening(self):
        """Starts the socket listening - called when becoming Leader"""
        if self.server:
            try:
                self.server.close()
            except:
                pass
        
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen()
        print(f"[COMMS] Listening on {self.host}:{self.port}", flush=True)

    def receive_connection(self):
        if not self.server:
            return None
        client, address = self.server.accept()
        print(f"[COMMS] Connected with {address}", flush=True)
        return client

    def handle(self, client, queue):
        """Pushes the events to a queue"""
        while True:
            try:
                data = client.recv(1024).decode("utf-8")
                if not data:
                    break
                if "}{" in data:
                    parts = data.replace("}{", "}|{").split("|")
                    for part in parts:
                        message = json.loads(part)
                        queue.put(message)
                else:
                    message = json.loads(data)
                    queue.put(message)
            except Exception as error:
                print(f"[COMMS] Connection closed or error: {error}", flush=True)
                break
        
        try:
            client.close()
        except:
            pass

    def handle_follower(self, client, queue):
        """Pushes the events to a queue"""
        while True:
            try:
                data = client.recv(1024).decode("utf-8")
                if not data:
                    break
                if "}{" in data:
                    parts = data.replace("}{", "}|{").split("|")
                    for part in parts:
                        message = json.loads(part)
                        queue.put(message)
                else:
                    message = json.loads(data)
                    if message["type"] == "ack":
                        print("ONACK", flush=True)
                        self.acks += 1
                    else:
                        queue.put(message)
            except Exception as error:
                print(f"[COMMS] Connection closed or error: {error}", flush=True)
                break
        
        try:
            client.close()
        except:
            pass

    def broadcast(self, clients, msg_type, data, tick):
        message = {"type": msg_type, "tick": tick, "data": data}
        
        if msg_type == "update":
            print(f"[COMMS] Broadcasting 'update' ({len(data)} events) at tick {tick}", flush=True)
        elif msg_type == "clock":
            print(f"[COMMS] Broadcasting 'clock' sync at tick {tick}", flush=True)

        try:
            msg_bytes = json.dumps(message).encode("utf-8")
            for client in clients:
                try:
                    client.send(msg_bytes)
                except:
                    pass
        except Exception as e:
            print(f"[COMMS] Broadcast error: {e}", flush=True)
