import json
from enum import Enum

class Direction(Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"

class GameState:
    def __init__(self, width=15, height=13):
        self.width = width
        self.height = height
        self.players = {}  # player_id -> {x, y}
        self.bombs = []    # [{x, y, timer, owner_id}]
        self.walls = self.generate_walls()
    
    def generate_walls(self):
        """Generate basic wall structure"""
        walls = set()
        # Border walls
        for x in range(self.width):
            walls.add((x, 0))
            walls.add((x, self.height - 1))
        for y in range(self.height):
            walls.add((0, y))
            walls.add((self.width - 1, y))
        
        # Internal walls (every other position)
        for x in range(2, self.width - 2, 2):
            for y in range(2, self.height - 2, 2):
                walls.add((x, y))
        
        return walls
    
    def to_dict(self):
        return {
            "width": self.width,
            "height": self.height,
            "players": self.players,
            "bombs": self.bombs,
            "walls": list(self.walls)
        }
    
    @staticmethod
    def from_dict(data):
        state = GameState(data["width"], data["height"])
        state.players = data["players"]
        state.bombs = data["bombs"]
        state.walls = set(tuple(w) for w in data["walls"])
        return state