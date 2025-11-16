import asyncio
import websockets
import pygame
import json
import sys
sys.path.append('..')
from shared.game_state import GameState

class GameClient:
    def __init__(self):
        pygame.init()
        
        # Game settings
        self.cell_size = 40
        self.width = 15
        self.height = 13
        
        # Create window
        self.screen = pygame.display.set_mode(
            (self.width * self.cell_size, self.height * self.cell_size)
        )
        pygame.display.set_caption("Bomberman")
        
        # Game state
        self.game_state = None
        self.player_id = None
        self.websocket = None
        
        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.GREEN = (0, 255, 0)
        self.PINK = (255,20,147)
        self.RED = (255, 0, 0)
        self.GRAY = (128, 128, 128)
        self.BLUE = (0, 0, 255)
    
    async def connect(self):
        self.websocket = await websockets.connect("ws://localhost:8765")
        
        # Receive initial state
        message = await self.websocket.recv()
        data = json.loads(message)
        
        if data["type"] == "init":
            self.player_id = data["player_id"]
            self.game_state = GameState.from_dict(data["state"])
            print(f"Connected as {self.player_id}")
    
    async def send_move(self, direction):
        if self.websocket:
            await self.websocket.send(json.dumps({
                "type": "move",
                "direction": direction
            }))
    
    async def send_place_bomb(self):
        if self.websocket:
            await self.websocket.send(json.dumps({
                "type": "place_bomb"
            }))
    
    async def receive_updates(self):
        """Listen for state updates from server"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                if data["type"] == "state_update":
                    self.game_state = GameState.from_dict(data["state"])
        except websockets.exceptions.ConnectionClosed:
            print("Connection to server closed")
    
    def draw(self):
        self.screen.fill(self.WHITE)
        
        if not self.game_state:
            return
        
        # Draw walls
        for x, y in self.game_state.walls:
            pygame.draw.rect(
                self.screen,
                self.BLACK,
                (x * self.cell_size, y * self.cell_size, 
                 self.cell_size, self.cell_size)
            )
        
        # Draw players
        for pid, player in self.game_state.players.items():
            color = self.PINK if pid == self.player_id else self.BLUE
            pygame.draw.circle(
                self.screen,
                color,
                (player["x"] * self.cell_size + self.cell_size // 2,
                 player["y"] * self.cell_size + self.cell_size // 2),
                self.cell_size // 3
            )
        
        # Draw bombs
        for bomb in self.game_state.bombs:
            pygame.draw.circle(
                self.screen,
                self.RED,
                (bomb["x"] * self.cell_size + self.cell_size // 2,
                 bomb["y"] * self.cell_size + self.cell_size // 2),
                self.cell_size // 4
            )
        
        pygame.display.flip()
    
    async def handle_input(self):
        """Handle keyboard input"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    await self.send_move("up")
                elif event.key == pygame.K_DOWN:
                    await self.send_move("down")
                elif event.key == pygame.K_LEFT:
                    await self.send_move("left")
                elif event.key == pygame.K_RIGHT:
                    await self.send_move("right")
                elif event.key == pygame.K_SPACE:
                    await self.send_place_bomb()
        
        return True
    
    async def run(self):
        await self.connect()
        
        # Start receiving updates in background
        asyncio.create_task(self.receive_updates())
        
        clock = pygame.time.Clock()
        running = True
        
        while running:
            running = await self.handle_input()
            self.draw()
            clock.tick(60)  # 60 FPS
            await asyncio.sleep(0)  # Allow other tasks to run
        
        pygame.quit()
        await self.websocket.close()

async def main():
    client = GameClient()
    await client.run()

if __name__ == "__main__":
    asyncio.run(main())