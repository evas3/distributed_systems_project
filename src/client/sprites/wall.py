import pygame
import os

dirname = os.path.dirname(__file__)

class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y, cell_size):
        super().__init__()
        self.pixel_x = x
        self.pixel_y = y

        original = pygame.image.load(
            os.path.join(dirname, "..", "assets", "Wall.png")
        ).convert_alpha()
        self.image = pygame.transform.scale(original, (cell_size, cell_size))

        self.rect = self.image.get_rect(topleft=(x, y))