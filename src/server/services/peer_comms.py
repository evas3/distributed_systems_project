import socket
import threading
import json
import time

class PeerComms:
    def __init__(self, server_id, peers, port, msg_queue):
        self.server_id = server_id
        self.peers = peers
        self.msg_queue = msg_queue
        self.current_leader = 99

        self.listener = None
        self.peer_sockets = {}
        self.peer_recv_threads = {}

        self._start_listener(port)
        self._connect_to_peers()

    def _start_listener(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", port))
        sock.listen()

        self.listener = sock

        thread = threading.Thread(target=self._accept_loop, daemon=True)
        thread.start()

    def _accept_loop(self):
        while True:
            conn, addr = self.listener.accept()
            raw = conn.recv(1024).decode("utf-8")
            msg = json.loads(raw)
            if msg["type"] == "peer_hello":
                new_msg = {
                    "type": "curr_leader",
                    "leader": self.current_leader,
                    "from": self.server_id
                }
                conn.send(json.dumps(new_msg).encode("utf-8"))
                peer_id = msg["server_id"]
                self.peer_sockets[peer_id] = conn
                self._start_recv_thread(conn)
    
    def _start_recv_thread(self, conn):
        t = threading.Thread(
            target=self._recv_loop,
            args=(conn,),
            daemon=True
        )
        t.start()

    def _recv_loop(self, conn):
        while True:
            try:
                data = conn.recv(4096)
                if not data:
                    return
                
                text = data.decode("utf-8")
                parts = text.replace("}{", "}|{").split("|")

                for chunk in parts:
                    msg = json.loads(chunk)
                    self.msg_queue.put(msg)

            except:
                return
            
    def _connect_to_peers(self):
        for (peer_id, ip, port) in self.peers:
            if peer_id == self.server_id:
                continue

            thread = threading.Thread(target=self._try_connect_peer, args=(peer_id, ip, port), daemon=True)
            thread.start()

    def _try_connect_peer(self, peer_id, ip, port):
        while peer_id not in self.peer_sockets:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((ip, port))
                self.peer_sockets[peer_id] = sock
                self._start_recv_thread(sock)

                handshake = {"type": "peer_hello", "server_id": self.server_id}
                sock.send(json.dumps(handshake).encode("utf-8"))
            except Exception as e:
                print(f"Couldn't connect to server {peer_id}", flush=True)
                time.sleep(1)

    def send_to_peer(self, peer_id, msg):
        if peer_id not in self.peer_sockets:
            return
        raw = json.dumps(msg).encode("utf-8")
        try:
            self.peer_sockets[peer_id].send(raw)
        except:
            self._drop_socket(self.peer_sockets[peer_id], peer_id)

    def broadcast(self, msg):
        raw = json.dumps(msg).encode("utf-8")
        dropped = []
        for peer_id, sock in self.peer_sockets.items():
            try:
                sock.send(raw)
            except:
                dropped.append((peer_id, sock))
        if dropped:
            for (peer_id, sock) in dropped:
                self._drop_socket(sock, peer_id)

    def _drop_socket(self, sock, key=None):
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except:
            pass

        try:
            sock.close()
        except:
            pass

        if key is not None:
            del self.peer_sockets[key]