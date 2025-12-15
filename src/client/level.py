import pygame
from sprites.player import Player
from objects.playerObject import PlayerObject
from sprites.floor import Floor
from sprites.wall import Wall
from objects.bombObject import BombObject
from objects.explosionObject import ExplosionObject
from sprites.bomb import Bomb
from sprites.explosion import Explosion
import time

class Level:
    def __init__(self, level_map, player_map, bomb_map, explosion_map, cell_size, event_queue, comms):
        self.cell_size = cell_size
        self.players = {}
        self.bombs = {}
        self.explosions = {}
        self.level_map = level_map
        self.player_map = player_map
        self.bomb_map = bomb_map
        self.explosion_map = explosion_map
        self.walls = pygame.sprite.Group()
        self.floors = pygame.sprite.Group()
        self.event_queue = event_queue
        
        self.comms = comms

        self.tick_interval = 1.0/60
        self.local_tick = 0
        self.max_clock_drift = 5

        self.global_explosion_id = 1

        self.static_sprites = pygame.sprite.Group()

        self._initialize_sprites(level_map)

    def _initialize_sprites(self, level_map):
        """initializes the level"""
        height = len(level_map)
        width = len(level_map[0])

        for y in range(height):
            for x in range(width):
                cell = level_map[y][x]
                normalized_x = x*self.cell_size
                normalized_y = y*self.cell_size

                if cell == 0:
                    self.floors.add(Floor(normalized_x, normalized_y, self.cell_size))
                elif cell == 1:
                    self.walls.add(Wall(normalized_x, normalized_y, self.cell_size))

        self.static_sprites.add(self.walls, self.floors)

        for y in range(height):
            for x in range(width):
                cell = self.player_map[y][x]
                normalized_x = x*self.cell_size
                normalized_y = y*self.cell_size

                if cell == 0:
                    continue
                else:
                    self.players[cell] = PlayerObject(cell, x, y, Player(normalized_x, normalized_y, self.cell_size))

    def update(self, dt):
        """updates all time-based events like player animations, bomb timers, and explosions"""
        for player in self.players.values():
            player.update(dt)

        while not self.comms.recv_queue.empty():
            msg = self.comms.recv_queue.get()
            
            if msg["type"] == "update":
                for event in msg["data"]:
                    self.handle_event(event["event_type"], event["data"])
            elif msg["type"] == "clock":
                server_tick = msg["data"]["server_tick"]
                latency = (time.perf_counter() - msg["data"]["timestamp"]) / 2
                server_tick = server_tick + int(latency / self.tick_interval)
                self.sync_local_tick(server_tick)

        events = self.event_queue.pop_ready(self.local_tick)
        for event in events:
            self.handle_event(event[1], event[2])

        self.local_tick += 1

    def render(self, screen):
        """renders all graphics"""
        self.static_sprites.draw(screen)

        for player in self.players.values():
            player.render(screen)

        for bomb in self.bombs.values():
            bomb.render(screen)

        for explosion in self.explosions.values():
            explosion.render(screen)

    def move_player(self, id, x, y):
        """checks if player can move, and sends event to server"""
        
        if id not in self.players:
            return
        
        player_x = self.players[id].x
        player_y = self.players[id].y
        new_x = player_x + x
        new_y = player_y + y

        if self.players[id].moving:
            return


        if (0 <= new_x < len(self.level_map[0])) and (0 <= new_y < len(self.level_map)):
            if self.level_map[new_y][new_x] != 0:
                return
            elif self.player_map[new_y][new_x] != 0:
                return
            elif self.bomb_map[new_y][new_x] != 0:
                return
            else:
                print(f"[CLIENT] Sending Move Request: {x}, {y}", flush=True)
                self.comms.send_event(2, [id, x, y, new_x, new_y])
                return

        else:
            return
        
    def handle_moving(self, data):
        player_id, x, y, new_x, new_y = data

        self.player_map[new_y-y][new_x-x] = 0
        self.player_map[new_y][new_x] = player_id
        self.players[player_id].move(x, y)

    def handle_moving_stop(self, data):
        player_id = data[0]
        self.players[player_id].moving = False

    def handle_dying(self, data):
        player_id, x, y = data
        self.player_map[y][x] = 0
        self.players[player_id].sprite.kill()
        del self.players[player_id]


    def lay_bomb(self, id):
        """spawns a new bomb object on the player coordinates"""
        if id not in self.players:
            return
        player = self.players[id]
        print(f"[CLIENT] Sending Bomb Request", flush=True)
        self.comms.send_event(0, [player.x, player.y, id])

    def spawn_bomb(self, x, y, id, owner, explosion_tick):
        self.bomb_map[y][x] = id
        self.bombs[id] = BombObject(id, x, y, owner, 120, Bomb(x*self.cell_size, y*self.cell_size, self.cell_size))
        self.event_queue.push(explosion_tick, 1, (id, x, y, owner))

    def explode_bomb(self, data):
        """removes the bomb object and spawns explosion objects"""
        if self.bombs.get(data[0]) is None:
            return
        self.bomb_map[data[2]][data[1]] = 0
        del self.bombs[data[0]]

        self.spawn_explosion(data[1], data[2], data[3])

        for direction in [(1,0), (-1,0), (0,1), (0,-1)]:
            nx = data[1] + direction[0]
            ny = data[2] + direction[1]
            if nx < 0 or nx > len(self.level_map[0]) - 1 or ny < 0 or ny > len(self.level_map) - 1:
                continue
            
            if self.level_map[ny][nx] != 0:
                continue

            self.spawn_explosion(nx, ny, data[3])

            if self.bomb_map[ny][nx] != 0:
                bomb_id = self.bomb_map[ny][nx]
                other_bomb = self.bombs[bomb_id]
                other_bomb.timer = 0
                continue

    def spawn_explosion(self, x, y, owner):
        """spawns new explosion object on given coordinates"""
        new_explosion = ExplosionObject(x, y, owner, 90, Explosion(x * self.cell_size, y * self.cell_size, self.cell_size))
        self.explosion_map[y][x] += 1
        self.explosions[self.global_explosion_id] = new_explosion
        self.event_queue.push(self.local_tick + 90, 3, (self.global_explosion_id, x, y))
        self.global_explosion_id += 1

    def remove_explosion(self, id):
        """removes given explosion object"""
        if id in self.explosions:
            explosion = self.explosions[id]
            self.explosion_map[explosion.y][explosion.x] -= 1
            del self.explosions[id]

    def handle_event(self, event_type, data):
        # 0 = bomb spawn,
        #  1 = bomb explode,
        #  2 = player moves,
        #  3 = remove explosion,
        #  4 = player stops moving
        #  5 = player dies
        match event_type:
            case 0:
                self.spawn_bomb(data[0], data[1], data[2], data[3], data[4])
            case 1:
                self.explode_bomb(data)
            case 2:
                self.handle_moving(data)
            case 3:
                self.remove_explosion(data[0])
            case 4:
                self.handle_moving_stop(data)
            case 5:
                self.handle_dying(data)

    def sync_local_tick(self, server_tick):
        difference = server_tick - self.local_tick

        if abs(difference) > self.max_clock_drift:
            print(f"[CLOCK] Adjusting local clock: {self.local_tick} -> {server_tick} (Diff: {difference})", flush=True)
            self.local_tick += difference
