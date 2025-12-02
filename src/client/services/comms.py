import socket
import json
import threading
from queue import Queue

class ServerComms():

    def __init__(self, host="127.0.0.1", port=55555):
        self.host = host
        self.port = port
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

        self.recv_queue = Queue()

        self.thread = threading.Thread(target=self._recv_loop, daemon=True)
        self.thread.start()
        
    def send_event(self, event_type, data):
        message = {"event_type": event_type, "data": data}
        message = json.dumps(message).encode("utf-8")
        self.sock.send(message)

    def _recv_loop(self):
        while True:
            try:
                data = self.sock.recv(4096).decode("utf-8")
                if not data:
                    break
                msg = json.loads(data)
                self.recv_queue.put(msg)
            except Exception as e:
                print("Network error:", e)
                break