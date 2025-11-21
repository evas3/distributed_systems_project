

class BombObject:
    def __init__(self, id, x, y, owner, timer, sprite):
        self.id = id
        self.x = x
        self.y = y
        self.owner = owner
        self.timer = timer
        self.sprite = sprite


    def update(self):
        self.timer -= 1

    def render(self, screen):
        self.sprite.render(screen)