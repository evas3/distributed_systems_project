import time
from queue import Queue
from objects.player import PlayerObject
from objects.bomb import BombObject
from objects.explosion import ExplosionObject
from leader import Leader
from follower import Follower
from services.peer_comms import PeerComms
from services.queue_service import EventQueue

class ServerLoop:
    def __init__(self, server_id, peers_config, peer_comms_config, level_map, player_map, bomb_map, explosion_map, tick_rate=60):
        self.server_id = server_id
        self.peers_config = peers_config
        self.peer_comms_config = peer_comms_config
        self.tick_rate = tick_rate
        self.tick_interval = 1.0 / tick_rate

        self.heartbeat_interval = 30
        self.last_heartbeat_sent = 0

        self.last_heartbeat_tick = 0
        self.heartbeat_timeout = 120
        
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
        self.event_queue = EventQueue()

        self.role_obj = Follower(self)
        self.leader_addr = None
        self.leader_id = None
        self.has_leader = False
        self.peer_queue = Queue()
        self.peer_comms = PeerComms(self.server_id, self.peer_comms_config, self.peer_comms_config[server_id-1][2], self.peer_queue)

        self.election_in_progress = False
        self.waiting_for_leader = False
        self.election_start_time = None
        self.election_timeout = 0.2

        self.initialize_players()

    def initialize_players(self):
        height = len(self.level_map)
        width = len(self.level_map[0])
        for y in range(height):
            for x in range(width):
                cell = self.player_map[y][x]
                if cell != 0:
                    self.players[cell] = PlayerObject(cell, x, y)

    def create_from_state(self):
        height = len(self.level_map)
        width = len(self.level_map[0])
        for y in range(height):
            for x in range(width):
                if self.bomb_map[y][x] != 0:
                    bomb_id = self.bomb_map[y][x]
                    self.bombs[bomb_id] = BombObject(bomb_id, x, y, 1)
                    self.bomb_map[y][x] = bomb_id
                    explode_tick = self.global_tick + 120
                    self.event_queue.push(explode_tick, 1, bomb_id)
                    self.global_bomb_id = max(self.global_bomb_id, bomb_id + 1)
                if self.explosion_map[y][x] != 0:
                    self.explosions[self.global_explosion_id] = ExplosionObject(x, y, 1)
                    self.global_explosion_id += 1

    def start(self):
        """Decides role based on ID and availability of peers"""
        print(f"Server {self.server_id} starting...", flush=True)

        self.leader_id = self.collect_leader_info()
        if self.leader_id != self.server_id:
            self.get_current_state()
            self.players = {}
            self.initialize_players()
            self.create_from_state()


        if self.leader_id >= self.server_id:
            self.become_leader()
        else:
            self.has_leader = True
            self.leader_addr = (self.peers_config[self.leader_id-1][1], self.peers_config[self.leader_id-1][2])
            self.peer_comms.current_leader = self.leader_id
        
        while True:
            if not self.has_leader:
                self.run_bully()
            self.waiting_for_leader = False
            result = self.role_obj.run()

            match result:
                case "NEED_ELECTION":
                    self.has_leader = False
                    continue
                case "DEMOTION":
                    self.role_obj = Follower(self)
                    continue
                case "LEADER_SWITCH":
                    continue
            

    def run_bully(self):
        print("Starting election", flush=True)

        self.start_election()
        self.election_in_progress = True

        while True:
            while not self.peer_queue.empty():
                msg = self.peer_queue.get()
                print(msg, flush=True)
                if msg["type"] == "leader_announce":
                    self.has_leader = True
                    self.role = Follower(self)
                    self.leader_id = msg["from"]
                    self.peer_comms.current_leader = self.leader_id
                    self.leader_addr = (self.peers_config[msg["from"] - 1][1], self.peers_config[msg["from"] - 1][2])
                    return
                elif msg["type"] == "bully_ok":
                    if msg["from"] < self.server_id:
                        self.waiting_for_leader = True
                    pass
                elif msg["type"] == "bully":
                    self.handle_bully(msg["from"])
                
            if not self.waiting_for_leader and self.election_timeout_expired():
                self.become_leader()
                return
            
            time.sleep(0.001)

    def start_election(self):
        msg = {
            "type": "bully",
            "from": self.server_id
        }

        self.peer_comms.broadcast(msg)
        print("Bully sent", flush=True)
        self.election_start_time = time.perf_counter()

    def handle_bully(self, from_id):
        msg = {
            "type": "bully_ok",
            "from": self.server_id
        }
        self.peer_comms.send_to_peer(from_id, msg)

    def become_leader(self):
        self.has_leader = True
        self.leader_id = self.server_id
        self.peer_comms.current_leader = self.server_id
        self.role_obj = Leader(self)
        self.send_leader_announce()

    def send_leader_announce(self):
        msg = {
            "type": "leader_announce",
            "from": self.server_id
        }
        self.peer_comms.broadcast(msg)

    def election_timeout_expired(self):
        if self.election_start_time is None:
            return False
        now = time.perf_counter()
        return (now - self.election_start_time) >= self.election_timeout
    
    def collect_leader_info(self, timeout=2.0):
        leader_ids = []
        start = time.perf_counter()

        while time.perf_counter() - start < timeout:
            while not self.peer_queue.empty():
                msg = self.peer_queue.get()
                if msg["type"] == "curr_leader":
                    leader_ids.append(msg["leader"])
            time.sleep(0.01)

        if leader_ids:
            return min(leader_ids)
        return self.server_id
    
    def get_current_state(self, timeout=2.0):
        self.peer_comms.send_to_peer(
            self.leader_id,
            {"type": "state_request", "from": self.server_id}
        )

        start = time.perf_counter()

        while time.perf_counter() - start < timeout:
            while not self.peer_queue.empty():
                msg = self.peer_queue.get()
                if msg["type"] == "curr_state":
                    self.level_map = msg["level_map"]
                    self.bomb_map = msg["bomb_map"]
                    self.player_map = msg["player_map"]
                    self.explosion_map = msg["explosion_map"]
                    return
            time.sleep(0.01)

    def send_current_state(self, peer_id):
        msg = {
            "type": "curr_state",
            "level_map": self.level_map,
            "bomb_map": self.bomb_map,
            "player_map": self.player_map,
            "explosion_map": self.explosion_map,
            "from": self.server_id
        }
        self.peer_comms.send_to_peer(peer_id, msg)
