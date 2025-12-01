import pygame
from level import Level
from client import Client

LEVEL_MAP = [[0, 0, 1, 0, 0],
             [0, 0, 1, 0, 0],
             [0, 0, 0, 0, 0],
             [0, 0, 1, 0, 0],
             [0, 0, 1, 0, 0]]

PLAYER_MAP = [[1, 0, 0, 0, 0],
              [0, 0, 0, 0, 0],
              [0, 0, 0, 0, 0],
              [0, 0, 0, 0, 0],
              [0, 0, 0, 0, 0],]

BOMB_MAP = [[0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],]

EXPLOSION_MAP = [[0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],]

CELL_SIZE = 100


def main():
    height = len(LEVEL_MAP)
    width = len(LEVEL_MAP[0])
    display_height = height * CELL_SIZE
    display_width = width * CELL_SIZE


    display = pygame.display.set_mode((display_width, display_height))

    pygame.display.set_caption("DisSysBomberman")
    level = Level(LEVEL_MAP, PLAYER_MAP, BOMB_MAP, EXPLOSION_MAP, CELL_SIZE)
    # TODO changing player ids
    game_loop = GameLoop(level, CELL_SIZE, display, 1, Client())

    pygame.init()
    game_loop.start_loop()



class GameLoop:
    def __init__(self, level, cell_size, display, player_id, client):
        self.client = client
        client.start()

        self._level = level
        self._clock = pygame.time.Clock()
        self._cell_size = cell_size
        self._display = display
        self._player_id = player_id

    def start_loop(self):
        while True:
            if self._handle_events() == False:
                break

            self._render()

            self._clock.tick(60)

    """sends the event to server or if quit closes connection"""
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    message = "left"
                if event.key == pygame.K_RIGHT:
                    message = "right"
                if event.key == pygame.K_UP:
                    message = "up"
                if event.key == pygame.K_DOWN:
                    message = "down"
                if event.key == pygame.K_SPACE:
                    message = "bomb"
                self.client.send(message, self._player_id)
            elif event.type == pygame.QUIT:
                self.client.close()
                return False


    def _render(self):
        self._level.update(5)
        self._level.render(self._display)
        
        pygame.display.update()

if __name__ == "__main__":
    main()