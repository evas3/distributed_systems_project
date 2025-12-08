class PlayerObject:
    def __init__(self, id, x, y):
        self.id = id
        self.x = x
        self.y = y
        self.moving = False
        self.alive = True

    def move(self, x, y):
        if not self.moving:
            self.x += x
            self.y += y
            self.moving = True