import socket
import json
import threading


class FollowerComms:
    def __init__(self, leader, id, queue):
        self.leader_addr = leader
        self.server_id = id
        self.socket = None
        self.queue = queue
        self.commit = False
        self.connect_to_leader()

    def connect_to_leader(self):
        """Connects to leader and starts a thread to receive messages"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(self.leader_addr)
        print(f"[FOLLOWER] Connected to Leader at {self.leader_addr}", flush=True)


        handshake = {
            "type": "server_hello",
            "server_id": self.server_id
        }

        sock.sendall((json.dumps(handshake)).encode("utf-8"))
        self.socket = sock

        thread = threading.Thread(
        target=self._recv_loop,
        daemon=True
        )
        thread.start()

    def _recv_loop(self):
        """Loop to receive messages and add them to message queue"""
        try:
            while True:
                data = self.socket.recv(4096).decode("utf-8")
                if not data:
                    raise Exception("Leader closed connection")
                try:
                    if "}{" in data:
                        parts = data.replace("}{", "}|{").split("|")
                        for part in parts:
                            self.queue.put(json.loads(part))
                    else:
                        msg = json.loads(data)
                        if msg["type"] == "commit":
                            self.commit = True
                        else:
                            self.queue.put(msg)
                except Exception as e:
                    print(f"[FOLLOWER] message error: {e}", flush=True)
        except Exception as e:
            print(f"[FOLLOWER] _recv_loop error: {e}", flush=True)

    def send_to_leader(self, msg):
        """Sends message to leader"""
        self.socket.send(json.dumps(msg).encode())

    def close_socket(self):
        """Closes socket to leader"""
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except:
            pass

        try:
            self.socket.close()
        except:
            pass
        
        self.socket = None