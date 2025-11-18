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
    def to_dict(self):
        return {
            "width": self.width,
            "height": self.height,
            "players": self.players,
            "bombs": self.bombs,
            "walls": list(self.walls),
            "matrix": self.to_matrix()
        }
    
    @staticmethod
    def from_dict(data):
        state = GameState(data["width"], data["height"])
        state.players = data["players"]
        state.bombs = data["bombs"]
        state.walls = set(tuple(w) for w in data["walls"])
        state.matrix = data.get("matrix")
        return state

    def to_matrix(self):
        """
        Build a 2D matrix representation of the game area.
        Empty cell -> 0
        Wall       -> -1
        Player     -> player_id  (string or int)
        """
        matrix = [[0 for _ in range(self.width)] for _ in range(self.height)]

        for x, y in self.walls:
            if 0 <= x < self.width and 0 <= y < self.height:
                matrix[y][x] = -1

        for pid, player in self.players.items():
            x, y = player["x"], player["y"]
            if 0 <= x < self.width and 0 <= y < self.height:
                matrix[y][x] = pid  # could be an int ID if you prefer

        return matrix
