

class PlayerObject:
    def __init__(self, id, x, y, sprite):
        self.id = id
        self.x = x
        self.y = y
        self.moving = False
        self.alive = True
        self.sprite = sprite

    def move(self, x, y):
        if not self.moving:
            self.x += x
            self.y += y
            self.moving = True


    def update(self, dt):
        if self.moving:
            done = self.sprite.update(dt, self.x, self.y)
            if done:
                self.moving = False

    def render(self, screen):
        self.sprite.render(screen)