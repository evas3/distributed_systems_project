import socket
import json
import threading
import time
from queue import Queue

class ServerComms():
    def __init__(self, servers_list):
        self.servers_list = servers_list
        self.current_server_index = 0
        self.sock = None
        self.connected = False
        
        self.recv_queue = Queue()

        self.thread = threading.Thread(target=self._connection_manager, daemon=True)
        self.thread.start()
        
    def send_event(self, event_type, data):
        if not self.connected or not self.sock:
            return
        try:
            message = {"event_type": event_type, "data": data}
            message = json.dumps(message).encode("utf-8")
            self.sock.send(message)
        except Exception:
            print("[NET] Send failed, waiting for reconnect...", flush=True)
            self.connected = False

    def _connection_manager(self):
        """Manages connecting and reconnecting to available servers"""
        while True:
            if not self.connected:
                self._try_connect()
            else:
                self._recv_loop()
            time.sleep(1)

    def _try_connect(self):
        for i in range(len(self.servers_list)):
            index = (self.current_server_index + i) % len(self.servers_list)
            target = self.servers_list[index]
            
            try:
                print(f"[NET] Attempting to connect to {target}...", flush=True)
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(5)
                self.sock.connect(target)
                self.sock.settimeout(None)

                handshake = {
                    "type": "client_hello"
                }
                self.sock.send((json.dumps(handshake)).encode("utf-8"))
                
                self.connected = True
                self.current_server_index = index
                print(f"[NET] Connected to {target}!", flush=True)

                self._receive_init()

                return
            except Exception as e:
                print(f"[NET] Failed to connect to {target}: {e}", flush=True)
                if self.sock:
                    try:
                        self.sock.close()
                    except:
                        pass
        
        print("[NET] All servers unreachable, retrying in 2s...", flush=True)
        time.sleep(2)

    def _receive_init(self):
        """Receives init message from server. Message contains maps etc"""
        try:
            data = self.sock.recv(1024).decode("utf-8")
            message = json.loads(data)
            print("MOI", message)
            if message["type"] == "init":
                self.level_map = message["data"]["level_map"]
                print("H", self.level_map)
                self.player_map = message["data"]["player_map"]
                self.bomb_map = message["data"]["bomb_map"]
                self.explosion_map = message["data"]["explosion_map"]
                self.local_player_id = message["data"]["local_player_id"]
        except Exception as e:
                print(f"[NET] Network error during receiving init: {e}", flush=True)


    def _recv_loop(self):
        while self.connected:
            try:
                data = self.sock.recv(4096).decode("utf-8")
                if not data:
                    print("[NET] Connection closed by server", flush=True)
                    self.connected = False
                    break

                if "}{" in data:
                    parts = data.replace("}{", "}|{").split("|")
                    for part in parts:
                        msg = json.loads(part)
                        self.recv_queue.put(msg)
                else:
                    msg = json.loads(data)
                    self.recv_queue.put(msg)
            except Exception as e:
                print(f"[NET] Network error during recv: {e}", flush=True)
                self.connected = False
                break
        
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
