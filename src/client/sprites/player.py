import pygame
import os

dirname = os.path.dirname(__file__)

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, cell_size):
        super().__init__()
        self.pixel_x = x
        self.pixel_y = y
        self.cell_size = cell_size
        original = pygame.image.load(
            os.path.join(dirname, "..", "assets", "Player.png")
        ).convert_alpha()
        self.image = pygame.transform.scale(original, (self.cell_size, self.cell_size))

        self.rect = self.image.get_rect(topleft=(x, y))

    def update(self, dt, x, y):
        nx = x*self.cell_size
        ny = y*self.cell_size
        if self.pixel_x != nx:
            if self.pixel_x < nx:
                self.pixel_x += dt
            else:
                self.pixel_x -= dt
            return False
        elif self.pixel_y != ny:
            if self.pixel_y < ny:
                self.pixel_y += dt
            else:
                self.pixel_y -= dt
            return False
        else:
            return True
        
    def render(self, screen):
        self.rect.topleft = (self.pixel_x, self.pixel_y)
        screen.blit(self.image, self.rect)