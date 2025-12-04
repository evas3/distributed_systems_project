import time
import socket
import json
import threading
from queue import Queue
from services.comms import ClientComms
from services.queue_service import EventQueue
from objects.bomb import BombObject
from objects.explosion import ExplosionObject
from objects.player import PlayerObject

class ServerLoop:
    def __init__(self, server_id, peers_config, level_map, player_map, bomb_map, explosion_map, tick_rate=60):
        self.server_id = server_id
        self.peers_config = peers_config
        self.tick_rate = tick_rate
        self.tick_interval = 1.0 / tick_rate
        
        self.global_tick = 0
        self.level_map = level_map
        self.player_map = player_map
        self.bomb_map = bomb_map
        self.explosion_map = explosion_map
        self.players = {}
        self.bombs = {}
        self.explosions = {}
        
        self.global_bomb_id = 1
        self.global_explosion_id = 1
        self.new_player_id = 1

        self.client_queues = {}
        self.event_queue = EventQueue()
        my_config = self.peers_config[self.server_id-1]
        self.comms = ClientComms(my_config[1], my_config[2])
        
        self.client_sockets = []
        self.outgoing_events = []
        self.last_tick = time.perf_counter()

        self.initialize_players()

    def initialize_players(self):
        height = len(self.level_map)
        width = len(self.level_map[0])
        for y in range(height):
            for x in range(width):
                cell = self.player_map[y][x]
                if cell != 0:
                    self.players[cell] = PlayerObject(cell, x, y)

    def start(self):
        """Decides role based on ID and availability of peers"""
        print(f"Server {self.server_id} loop running...", flush=True)
        
        while True:
            am_i_leader = True
            leader_info = None

            print(f"[CONSENSUS] Server {self.server_id} checking peers...", flush=True)

            for peer_id, ip, port in self.peers_config:
                if peer_id < self.server_id:
                    if self.check_connection(ip, port):
                        am_i_leader = False
                        leader_info = (ip, port)
                        print(f"[CONSENSUS] Found superior peer {peer_id} at {ip}:{port}", flush=True)
                        break
            
            if am_i_leader:
                print(f"[ROLE] Server {self.server_id} became LEADER", flush=True)
                self.run_leader()
            else:
                print(f"[ROLE] Server {self.server_id} became FOLLOWER (Leader is {leader_info})", flush=True)
                self.run_follower(leader_info)
            
            print("[FAILOVER] Role change detected, re-evaluating...", flush=True)
            time.sleep(1)

    def check_connection(self, ip, port):
        """Pings a server to see if it is alive"""
        try:
            s = socket.create_connection((ip, port), timeout=0.5)
            s.close()
            return True
        except:
            return False

    # LEADER LOGIC

    def run_leader(self):
        self.comms.start_listening()
        
        accept_thread = threading.Thread(target=self.accept_clients, daemon=True)
        accept_thread.start()

        self.last_tick = time.perf_counter()
        
        while True:
            now = time.perf_counter()
            if now - self.last_tick >= self.tick_interval:
                self.global_tick += 1
                self.last_tick += self.tick_interval

                if self.global_tick % 60 == 0:
                    print(f"[LEADER] Global Tick: {self.global_tick}", flush=True)

                if self.global_tick % 50 == 0:
                    self.send_clock_sync()

                self.outgoing_events = []

                self.process_inputs()
                self.handle_events()
                
                self.broadcast_state()

            time.sleep(0.0005)


    def accept_clients(self):
        while True:
            try:
                sock = self.comms.receive_connection()
                if not sock:
                    continue
                
                print(f"[NET] Accepted new connection", flush=True)
                self.client_sockets.append(sock)
                
                client_q = Queue()
                self.client_queues[sock] = client_q
                
                thread = threading.Thread(
                    target=self.comms.handle,
                    args=(sock, client_q),
                    daemon=True
                )
                thread.start()
                
                if self.new_player_id <= 4: 
                    self.new_player_id += 1
            except Exception as e:
                print(f"[NET] Accept error: {e}", flush=True)
                break

    def broadcast_state(self):
        if len(self.outgoing_events) == 0:
            return
        
        active_sockets = []
        for sock in self.client_sockets:
            try:
                self.comms.broadcast([sock], "update", self.outgoing_events, self.global_tick)
                active_sockets.append(sock)
            except:
                print("[NET] Client/Follower disconnected during broadcast", flush=True)
                if sock in self.client_queues:
                    del self.client_queues[sock]
        
        self.client_sockets = active_sockets

    # FOLLOWER LOGIC

    def run_follower(self, leader_address):
        """Follower connects to leader and mirrors state"""
        try:
            if self.comms.server:
                self.comms.server.close()
                self.comms.server = None

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(leader_address)
            print(f"[FOLLOWER] Connected to Leader at {leader_address}", flush=True)
            
            while True:
                data = sock.recv(4096).decode("utf-8")
                if not data:
                    raise Exception("Leader closed connection")
                try:
                    if "}{" in data:
                        parts = data.replace("}{", "}|{").split("|")
                        for part in parts:
                            self.process_follower_message(json.loads(part))
                    else:
                        self.process_follower_message(json.loads(data))
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            print(f"[FOLLOWER] Connection to Leader lost: {e}", flush=True)
            return

    def process_follower_message(self, message):
        if message["type"] == "update":
            for event in message["data"]:
                self.parse_event(event["event_type"], event["data"])
            self.global_tick = message["tick"]
            
            if self.global_tick % 60 == 0:
                print(f"[FOLLOWER] Synced Tick: {self.global_tick}", flush=True)

    # SHARED LOGIC

    def process_inputs(self):
        for client, q in self.client_queues.items():
            while not q.empty():
                msg = q.get()
                print(f"[INPUT] Received {msg['event_type']} from client", flush=True)
                self.handle_input(client, msg)

    def handle_input(self, client, msg):
        self.parse_event(msg["event_type"], msg["data"])

    def handle_events(self):
        ready = self.event_queue.pop_ready(self.global_tick)
        for event in ready:
            self.parse_event(event[1], event[2])


    def parse_event(self, event_type, event_data):
        # 0 = bomb spawn,
        #  1 = bomb explode,
        #  2 = player moves,
        #  3 = remove explosion,
        #  4 = player stop
        match event_type:
            case 0: self.spawn_bomb(event_data)
            case 1: self.explode_bomb(event_data)
            case 2: self.move_player(event_data)
            case 3: self.remove_explosion(event_data[0], event_data[1], event_data[2])
            case 4: self.finish_moving(event_data)

    def spawn_bomb(self, data):
        x, y = data[0], data[1]
        
        bomb_id = data[2]
        owner = data[3]
        explode_tick = data[4]

        if self.bomb_map[y][x] == 0:
            self.bombs[bomb_id] = BombObject(bomb_id, x, y, owner)
            self.bomb_map[y][x] = bomb_id
        
        if self.outgoing_events is not None: 
            self.event_queue.push(explode_tick, 1, bomb_id)
            self.outgoing_events.append({"event_type": 0, "data": [x, y, bomb_id, owner, explode_tick]})

        if bomb_id >= self.global_bomb_id: self.global_bomb_id = bomb_id + 1

    def explode_bomb(self, data):
        bomb_id = data
        if self.bombs.get(bomb_id) is None: return
        x, y, owner = self.bombs[bomb_id].x, self.bombs[bomb_id].y, self.bombs[bomb_id].owner
        self.bomb_map[y][x] = 0
        del self.bombs[bomb_id]

        self.spawn_explosion(x, y, owner)

        for direction in [(1,0), (-1,0), (0,1), (0,-1)]:
            nx, ny = x + direction[0], y + direction[1]
            if 0 <= nx < len(self.level_map[0]) and 0 <= ny < len(self.level_map):
                if self.level_map[ny][nx] == 0:
                    self.spawn_explosion(nx, ny, owner)
                    if self.bomb_map[ny][nx] != 0:
                        chain_id = self.bomb_map[ny][nx]
                        if self.outgoing_events is not None:
                            self.event_queue.push(self.global_tick, 1, chain_id)
                            self.outgoing_events.append({"event_type": 0, "data": [nx, ny, chain_id, self.bombs[chain_id].owner, self.global_tick]})

    def spawn_explosion(self, x, y, owner):
        exp_id = self.global_explosion_id
        new_explosion = ExplosionObject(x, y, owner)
        self.explosion_map[y][x] += 1
        self.explosions[exp_id] = new_explosion
        
        if self.outgoing_events is not None:
            self.event_queue.push(self.global_tick + 90, 3, (exp_id, x, y))
        
        self.global_explosion_id += 1

    def remove_explosion(self, id, x, y):
        if id in self.explosions:
            self.explosion_map[y][x] -= 1
            del self.explosions[id]

    def move_player(self, data):
        player_id, x, y, new_x, new_y = data
        self.player_map[y][x] = 0
        self.player_map[new_y][new_x] = player_id
        if player_id in self.players:
            self.players[player_id].move(x, y) 
            self.players[player_id].x = new_x
            self.players[player_id].y = new_y

        if self.outgoing_events is not None:
            self.outgoing_events.append({"event_type": 2, "data": [player_id, x, y, new_x, new_y]})
            self.event_queue.push(self.global_tick + 20, 4, player_id)

    def finish_moving(self, data):
        player_id = data
        if player_id in self.players:
            self.players[player_id].moving = False
        if self.outgoing_events is not None:
            self.outgoing_events.append({"event_type": 4, "data": [player_id]})

    def send_clock_sync(self):
        tick = self.global_tick
        timestamp = time.perf_counter()
        print(f"[CLOCK] Syncing clients to tick {tick}", flush=True)
        self.comms.broadcast(self.client_sockets, "clock", {"server_tick": tick, "timestamp": timestamp}, tick)
