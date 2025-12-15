import pygame
import time
from level import Level
from services.queue_service import EventQueue
from services.comms import ServerComms

SERVERS_LIST = [
    ("127.0.0.1", 55533),
    ("127.0.0.1", 55534),
    ("127.0.0.1", 55535)
]

CELL_SIZE = 100

def main():
    comms = ServerComms(SERVERS_LIST)
    while not hasattr(comms, 'local_player_id'):
        time.sleep(1)
    event_queue = EventQueue()

    height = len(comms.level_map)
    width = len(comms.level_map[0])
    display_height = height * CELL_SIZE
    display_width = width * CELL_SIZE

    display = pygame.display.set_mode((display_width, display_height))
    level = Level(comms.level_map, comms.player_map, comms.bomb_map, comms.explosion_map, CELL_SIZE, event_queue, comms, comms.local_player_id)
    pygame.display.set_caption("DisSysBomberman Client")
    game_loop = GameLoop(level, CELL_SIZE, display, comms.local_player_id)

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
        return True

    def _render(self):
        self._level.update(5)
        self._level.render(self._display)
        if self._level.dead:
            overlay = pygame.Surface(self._display.get_size())
            overlay.fill((0, 0, 0))
            self._display.blit(overlay, (0, 0))

            text = pygame.font.SysFont("Arial", 30).render("You lost", True, (255, 0, 0))
            rect = text.get_rect(center=self._display.get_rect().center)
            self._display.blit(text, rect)
        pygame.display.update()

if __name__ == "__main__":
    main()
