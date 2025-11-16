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