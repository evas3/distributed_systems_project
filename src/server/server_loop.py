import time
import socket
from objects.player import PlayerObject
from leader import Leader
from follower import Follower

class ServerLoop:
    def __init__(self, server_id, peers_config, level_map, player_map, bomb_map, explosion_map, tick_rate=60):
        self.server_id = server_id
        self.peers_config = peers_config
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

        self.role_obj = None

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
                self.role_obj = Leader(self)

                self.role_obj.run_leader()
            else:
                print(f"[ROLE] Server {self.server_id} became FOLLOWER (Leader is {leader_info})", flush=True)
                self.role_obj = Follower(leader_info, self)

                self.role_obj.run_follower()
            
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

    