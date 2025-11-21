import pygame
import os

dirname = os.path.dirname(__file__)

class Bomb(pygame.sprite.Sprite):
    def __init__(self, x, y, cell_size):
        super().__init__()
        self.pixel_x = x
        self.pixel_y = y
        self.cell_size = cell_size

        original = pygame.image.load(
            os.path.join(dirname, "..", "assets", "Bomb.png")
        ).convert_alpha()
        self.image = pygame.transform.scale(original, (self.cell_size, self.cell_size))

        self.rect = self.image.get_rect(topleft=(x, y))

    def render(self, screen):
        self.rect.topleft = (self.pixel_x, self.pixel_y)
        screen.blit(self.image, self.rect)