import pygame
from sprites.player import Player
from objects.playerObject import PlayerObject
from sprites.floor import Floor
from sprites.wall import Wall
from objects.bombObject import BombObject
from objects.explosionObject import ExplosionObject
from sprites.bomb import Bomb
from sprites.explosion import Explosion
from services.comms import ServerComms


class Level:
    def __init__(self, level_map, player_map, bomb_map, explosion_map, cell_size, event_queue):
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
        
        self.comms = ServerComms()


        self.local_tick = 0

        self.global_bomb_id = 1
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
        """checks if player can move, and moves if so"""
        
        player_x = self.players[id].x
        player_y = self.players[id].y
        new_x = player_x + x
        new_y = player_y + y

        if self.players[id].moving:
            return False

        if (0 <= new_x < len(self.level_map[0])) and (0 <= new_y < len(self.level_map)):
            if self.level_map[new_y][new_x] != 0:
                return False
            elif self.player_map[new_y][new_x] != 0:
                return False
            elif self.bomb_map[new_y][new_x] != 0:
                return False
            else:
                self.player_map[player_y][player_x] = 0
                self.player_map[new_y][new_x] = id
                self.players[id].move(x, y)
                return True

        else:
            return False
        
    def lay_bomb(self, id):
        """spawns a new bomb object on the player coordinates"""
        player = self.players[id]
        self.comms.send_event(0, {"x":player.x, "y":player.y, "player": id})
        self.spawn_bomb(self.local_tick + 120, self.global_bomb_id, player.x, player.y, id)
        self.global_bomb_id += 1

    def spawn_bomb(self, explosion_tick, id, x, y, owner):
        self.bomb_map[y][x] = id
        self.bombs[id] = BombObject(id, x, y, owner, 120, Bomb(x*self.cell_size, y*self.cell_size, self.cell_size))
        self.event_queue.push(explosion_tick, 1, (id, x, y, owner))

        
    def explode_bomb(self, data):
        """removes the bomb object and spawns explosion objects"""
        # data = (id, x, y, owner)
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
        explosion = self.explosions[id]
        self.explosion_map[explosion.y][explosion.x] -= 1
        del self.explosions[id]

    # TODO def kill_player(self, id)

    def handle_event(self, event_type, data):
        # 0 = bomb spawn
        # 1 = bomb explode
        # 2 = player moves
        # 3 = remove explosion

        match event_type:
            case 0:
                self.spawn_bomb(data[0], data[1], data[2], data[3], data[4])
            case 1:
                self.explode_bomb(data)
            case 2:
                pass
            case 3:
                self.remove_explosion(data[0])