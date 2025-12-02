import time
from queue import Queue
from services.comms import ClientComms
from services.queue_service import EventQueue
from objects.bomb import BombObject
from objects.explosion import ExplosionObject
from objects.player import PlayerObject
import threading

class ServerLoop:
    def __init__(self, level_map, player_map, bomb_map, explosion_map, tick_rate=60):
        self.tick_rate = tick_rate
        self.global_tick = 0
        self.tick_interval = 1.0 / tick_rate

        self.players = {}
        self.bombs = {}
        self.explosions = {}

        self.level_map = level_map
        self.player_map = player_map
        self.bomb_map = bomb_map
        self.explosion_map = explosion_map

        self.global_bomb_id = 1
        self.global_explosion_id = 1

        self.new_player_id = 1

        self.client_queues = {}
        self.event_queue = EventQueue()

        self.comms = ClientComms()
        self.client_sockets = []

        self.outgoing_events = []

        self.wait_for_clients()
        self.initialize_players()
        # TODO send maps to the players
        self.last_tick = time.perf_counter()



    def initialize_players(self):
        height = len(self.level_map)
        width = len(self.level_map[0])

        for y in range(height):
            for x in range(width):
                cell = self.player_map[y][x]
                if cell == 0:
                    continue
                else:
                    self.players[cell] = PlayerObject(cell, x, y)

    def start_loop(self):
        while True:
            now = time.perf_counter()

            if now - self.last_tick >= self.tick_interval:
                self.global_tick += 1
                self.last_tick += self.tick_interval

                if self.global_tick % 50 == 0:
                    self.send_clock_sync()

                self.outgoing_events = []

                self.process_inputs()
                self.handle_events()
                self.broadcast_events_to_clients()

            time.sleep(0.0005)
    
    def process_inputs(self):
        for client, q in self.client_queues.items():
            while not q.empty():
                msg = q.get()
                self.handle_input(client, msg)

    def handle_events(self):
        ready = self.event_queue.pop_ready(self.global_tick)
        for event in ready:
            self.parse_event(event[1], event[2])

    def parse_event(self, event_type, event_data):
        # 0 = bomb spawn
        # 1 = bomb explode
        # 2 = player moves
        # 3 = remove explosion
        # 4 = player stops moving
        match event_type:
            case 0:
                self.spawn_bomb(event_data)
            case 1:
                self.explode_bomb(event_data)
            case 2:
                self.move_player(event_data)
            case 3:
                self.remove_explosion(event_data[0], event_data[1], event_data[2])
            case 4:
                self.finish_moving(event_data)

    def spawn_bomb(self, data):
        x, y = data[0], data[1]

        if self.bomb_map[y][x] != 0:
            return

        bomb_id = self.global_bomb_id
        owner = data[2]

        self.bombs[bomb_id] = BombObject(bomb_id, x, y, owner)
        self.bomb_map[y][x] = bomb_id

        explode_tick = self.global_tick + 120
        self.event_queue.push(explode_tick, 1, bomb_id)
        self.outgoing_events.append({"event_type": 0, "data": [x, y, bomb_id, owner, explode_tick]})

        self.global_bomb_id += 1

    def explode_bomb(self, data):
        bomb_id = data
        if self.bombs.get(bomb_id) is None:
            #already exploded
            return
        x, y, owner = self.bombs[bomb_id].x, self.bombs[bomb_id].y, self.bombs[bomb_id].owner
        self.bomb_map[y][x] = 0
        del self.bombs[bomb_id]

        self.spawn_explosion(x, y, owner)

        for direction in [(1,0), (-1,0), (0,1), (0,-1)]:
            nx = x + direction[0]
            ny = y + direction[1]
            if nx < 0 or nx > len(self.level_map[0]) - 1 or ny < 0 or ny > len(self.level_map) - 1:
                continue
            
            if self.level_map[ny][nx] != 0:
                continue
            self.spawn_explosion(nx, ny, owner)

            if self.bomb_map[ny][nx] != 0:
                chain_bomb_id = self.bomb_map[ny][nx]
                self.event_queue.push(self.global_tick, 1, chain_bomb_id)
                self.outgoing_events.append({"event_type": 0, "data": [nx, ny, chain_bomb_id, self.bombs[chain_bomb_id].owner, self.global_tick]})
                continue

    def spawn_explosion(self, x, y, owner):
        new_explosion = ExplosionObject(x, y, owner)
        self.explosion_map[y][x] += 1
        self.explosions[self.global_explosion_id] = new_explosion
        self.event_queue.push(self.global_tick + 90, 3, (self.global_explosion_id, x, y))
        self.global_explosion_id += 1

    def remove_explosion(self, id, x, y):
        """removes given explosion object"""
        self.explosion_map[y][x] -= 1
        del self.explosions[id]

    def move_player(self, data):
        player_id, x, y = data[0], data[1], data[2]

        player_x = self.players[player_id].x
        player_y = self.players[player_id].y
        new_x = player_x + x
        new_y = player_y + y

        if self.players[player_id].moving:
            return

        if (0 <= new_x < len(self.level_map[0])) and (0 <= new_y < len(self.level_map)):
            if self.level_map[new_y][new_x] != 0:
                return
            elif self.player_map[new_y][new_x] != 0:
                return
            elif self.bomb_map[new_y][new_x] != 0:
                return
            else:
                self.player_map[player_y][player_x] = 0
                self.player_map[new_y][new_x] = player_id
                self.players[player_id].move(x, y)

                self.outgoing_events.append({"event_type": 2, "data": [player_id, x, y, new_x, new_y]})
                self.event_queue.push(self.global_tick + 20, 4, player_id)
        else:
            return
        
    def finish_moving(self, data):
        player_id = data
        self.players[player_id].moving = False
        self.outgoing_events.append({"event_type": 4, "data": [player_id]})


    def handle_input(self, client, msg):
        print(msg["event_type"], flush=True)
        self.parse_event(msg["event_type"], msg["data"])

    def wait_for_clients(self, max_players=1):
        while (self.new_player_id <= max_players):
            client_socket = self.comms.receive_connection()
            self.client_sockets.append(client_socket)
            # TODO send the player id to the client

            client_q = Queue()
            self.client_queues[client_socket] = client_q

            thread = threading.Thread(
                target=self.comms.handle,
                args=(client_socket, client_q),
                daemon=True
            )

            thread.start()
            self.new_player_id += 1

    def broadcast_events_to_clients(self):
        if len(self.outgoing_events) == 0:
            return
        self.comms.broadcast(self.client_sockets, "update", self.outgoing_events, self.global_tick)

    def send_clock_sync(self):
        tick = self.global_tick
        timestamp = time.perf_counter()

        self.comms.broadcast(self.client_sockets, "clock", {"server_tick": tick, "timestamp": timestamp}, tick)