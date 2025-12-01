import pygame
from client.level import Level
from services.queue_service import EventQueue

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
    event_queue = EventQueue()
    level = Level(LEVEL_MAP, PLAYER_MAP, BOMB_MAP, EXPLOSION_MAP, CELL_SIZE, event_queue)
    game_loop = GameLoop(level, CELL_SIZE, display, 1)


    pygame.init()
    game_loop.start()

    


class GameLoop:
    def __init__(self, level, cell_size, display, player_id):
        self._level = level
        self._clock = pygame.time.Clock()
        self._cell_size = cell_size
        self._display = display
        self._player_id = player_id

    def start(self):
        while True:
            if self._handle_events() == False:
                break

            self._render()

            self._clock.tick(60)

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self._level.move_player(self._player_id, -1, 0)
                if event.key == pygame.K_RIGHT:
                    self._level.move_player(self._player_id, 1, 0)
                if event.key == pygame.K_UP:
                    self._level.move_player(self._player_id, 0, -1)
                if event.key == pygame.K_DOWN:
                    self._level.move_player(self._player_id, 0, 1)
                if event.key == pygame.K_SPACE:
                    self._level.lay_bomb(self._player_id)
            elif event.type == pygame.QUIT:
                return False

    def _render(self):
        self._level.update(5)
        self._level.render(self._display)
        
        pygame.display.update()

if __name__ == "__main__":
    main()