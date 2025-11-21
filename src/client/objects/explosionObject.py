class ExplosionObject:
    def __init__(self, x, y, owner, timer, sprite):
        self.x = x
        self.y = y
        self.owner = owner
        self.timer = timer
        self.sprite = sprite


    def update(self):
        self.timer -= 1

    def render(self, screen):
        self.sprite.render(screen)