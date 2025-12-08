import time
from queue import Queue
from services.follower_comms import FollowerComms
from services.queue_service import EventQueue
from objects.bomb import BombObject
from objects.explosion import ExplosionObject

class Follower:
    def __init__(self, leader_addr, server_loop):
        self.leader_queue = Queue()
        self.leader_addr = leader_addr
        self.server_loop = server_loop

        self.comms = FollowerComms(leader_addr, server_loop.server_id, self.leader_queue)

        self.event_queue = EventQueue()

        self.last_tick = time.perf_counter()

    def run_follower(self):
        """Follower connects to leader and mirrors state"""
        try:

            self.comms.connect_to_leader()
            self.server_loop.last_heartbeat_tick = self.server_loop.global_tick
            
            self.last_tick = time.perf_counter()
        
            while True:
                now = time.perf_counter()
                if now - self.last_tick >= self.server_loop.tick_interval:
                    self.server_loop.global_tick += 1
                    self.last_tick += self.server_loop.tick_interval

                    self.process_follower_messages()

                time.sleep(0.0005)

                if self.server_loop.global_tick - self.server_loop.last_heartbeat_tick > self.server_loop.heartbeat_timeout:
                    print(self.server_loop.global_tick, self.server_loop.last_heartbeat_tick)
                    print("[FOLLOWER] Leader timed out, starting election.")
                    raise Exception

        except Exception as e:
            print(f"[FOLLOWER] Connection to Leader lost: {e}", flush=True)
            return
        
    def process_follower_messages(self):
        while not self.leader_queue.empty():
                msg = self.leader_queue.get()
                print(f"[INPUT] Received {msg['type']} from leader", flush=True)
                self.process_follower_message(msg)

    def process_follower_message(self, message):
        if message["type"] == "event":
            ack = {
                "type": "ack",
                "tick": message["tick"]
            }
            self.comms.send_to_leader(ack)
            if not self.wait_for_commit(self.server_loop.global_tick):
                self.process_follower_message(message)
                return
            for event in message["data"]:
                self.parse_event(event["event_type"], event["data"])
        
        elif message["type"] == "heartbeat":
            leader_tick = message["tick"]
            self.sync_clock_to_leader(leader_tick)
            self.server_loop.last_heartbeat_tick = self.server_loop.global_tick

    def wait_for_commit(self, tick):
        #TODO ADD TIMEOUT
        while not self.comms.commit:
            time.sleep(0.0005)
            continue
        if self.comms.commit:
            self.comms.commit = False
            return True

    def sync_clock_to_leader(self, tick):
        self.server_loop.global_tick = tick

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

        if self.server_loop.bomb_map[y][x] == 0:
            self.server_loop.bombs[bomb_id] = BombObject(bomb_id, x, y, owner)
            self.server_loop.bomb_map[y][x] = bomb_id
        
        self.event_queue.push(explode_tick, 1, bomb_id)
        self.server_loop.global_bomb_id = bomb_id + 1

    def explode_bomb(self, data):
        bomb_id = data
        if self.server_loop.bombs.get(bomb_id) is None: return
        x, y, owner = self.server_loop.bombs[bomb_id].x, self.server_loop.bombs[bomb_id].y, self.server_loop.bombs[bomb_id].owner
        self.server_loop.bomb_map[y][x] = 0
        del self.server_loop.bombs[bomb_id]

        self.spawn_explosion(x, y, owner)

        for direction in [(1,0), (-1,0), (0,1), (0,-1)]:
            nx, ny = x + direction[0], y + direction[1]
            if 0 <= nx < len(self.server_loop.level_map[0]) and 0 <= ny < len(self.server_loop.level_map):
                if self.server_loop.level_map[ny][nx] == 0:
                    self.spawn_explosion(nx, ny, owner)
                    if self.server_loop.bomb_map[ny][nx] != 0:
                        chain_id = self.server_loop.bomb_map[ny][nx]
                        self.event_queue.push(self.server_loop.global_tick, 1, chain_id)

    def spawn_explosion(self, x, y, owner):
        exp_id = self.global_explosion_id
        new_explosion = ExplosionObject(x, y, owner)
        self.server_loop.explosion_map[y][x] += 1
        self.server_loop.explosions[exp_id] = new_explosion
        
        self.event_queue.push(self.server_loop.global_tick + 90, 3, (exp_id, x, y))
        
        self.global_explosion_id += 1

    def remove_explosion(self, id, x, y):
        if id in self.server_loop.explosions:
            self.server_loop.explosion_map[y][x] -= 1
            del self.server_loop.explosions[id]

    def move_player(self, data):
        player_id, x, y = data[0], data[1], data[2]
        player_x = self.server_loop.players[player_id].x
        player_y = self.server_loop.players[player_id].y
        new_x = player_x + x
        new_y = player_y + y
        if self.server_loop.players[player_id].moving:
            return
        if (0 <= new_x < len(self.server_loop.level_map[0])) and (0 <= new_y < len(self.server_loop.level_map)):
            if self.server_loop.level_map[new_y][new_x] != 0:
                return
            elif self.server_loop.player_map[new_y][new_x] != 0:
                return
            elif self.server_loop.bomb_map[new_y][new_x] != 0:
                return
            else:
                self.server_loop.player_map[player_y][player_x] = 0
                self.server_loop.player_map[new_y][new_x] = player_id
                self.server_loop.players[player_id].move(x, y)
                self.event_queue.push(self.server_loop.global_tick + 20, 4, player_id)

    def finish_moving(self, data):
        player_id = data[0]
        if player_id in self.server_loop.players:
            self.server_loop.players[player_id].moving = False