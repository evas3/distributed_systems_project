import pygame
from sprites.player import Player
from objects.playerObject import PlayerObject
from sprites.floor import Floor
from sprites.wall import Wall
from objects.bombObject import BombObject
from objects.explosionObject import ExplosionObject
from sprites.bomb import Bomb
from sprites.explosion import Explosion

class Level:
    def __init__(self, level_map, player_map, bomb_map, explosion_map, cell_size):
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

        self.global_bomb_id = 1

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

        exploded = []

        for bomb in self.bombs.values():
            bomb.update()
            if bomb.timer <= 0:
                exploded.append(bomb)

        removed = []
        for explosion in self.explosions.values():
            explosion.update()
            if self.player_map[explosion.y][explosion.x] != 0:
                player_id = self.player_map[explosion.y][explosion.x]
                #self.kill_player(player_id)
            if explosion.timer <= 0:
                removed.append(explosion)

        for bomb in exploded:
            self.explode_bomb(bomb)

        for explosion in removed:
            self.remove_explosion(explosion)

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

        if self.bomb_map[player.y][player.x] != 0:
            return False
        self.bomb_map[player.y][player.x] = self.global_bomb_id
        self.bombs[self.global_bomb_id] = BombObject(self.global_bomb_id, player.x, player.y, id, 120, Bomb(player.x * self.cell_size, player.y * self.cell_size, self.cell_size))
        self.global_bomb_id += 1


    def explode_bomb(self, bomb):
        """removes the bomb object and spawns explosion objects"""
        self.bomb_map[bomb.y][bomb.x] = 0
        del self.bombs[bomb.id]

        self.spawn_explosion(bomb.x, bomb.y, bomb.owner)

        for direction in [(1,0), (-1,0), (0,1), (0,-1)]:
            nx = bomb.x + direction[0]
            ny = bomb.y + direction[1]
            if nx < 0 or nx > len(self.level_map[0]) - 1 or ny < 0 or ny > len(self.level_map) - 1:
                continue
            
            if self.level_map[ny][nx] != 0:
                continue
            self.spawn_explosion(nx, ny, bomb.owner)

            if self.bomb_map[ny][nx] != 0:
                bomb_id = self.bomb_map[ny][nx]
                other_bomb = self.bombs[bomb_id]
                other_bomb.timer = 0
                continue
    
    def spawn_explosion(self, x, y, owner):
        """spawns new explosion object on given coordinates"""
        if self.explosion_map[y][x] != 0:
            return False
        new_explosion = ExplosionObject(x, y, owner, 90, Explosion(x * self.cell_size, y * self.cell_size, self.cell_size))
        self.explosion_map[y][x] = 1
        self.explosions[(x,y)] = new_explosion

    def remove_explosion(self, explosion):
        """removes given explosion object"""
        self.explosion_map[explosion.y][explosion.x] = 0
        del self.explosions[(explosion.x, explosion.y)]

    # TODO def kill_player(self, id)