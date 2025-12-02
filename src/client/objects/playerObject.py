

class PlayerObject:
    def __init__(self, id, x, y, sprite):
        self.id = id
        self.x = x
        self.y = y
        self.moving = False
        self.alive = True
        self.sprite = sprite

    def move(self, x, y):
        self.x += x
        self.y += y
        self.moving = True


    def update(self, dt):
        if self.moving:
            self.sprite.update(dt, self.x, self.y)

    def render(self, screen):
        self.sprite.render(screen)