import asyncio
import websockets
import json
import sys
sys.path.append('..')
from shared.game_state import GameState

class GameServer:
    def __init__(self):
        self.game_state = GameState()
        self.clients = {}  # websocket -> player_id
        self.next_player_id = 0
        self.game_state.walls = self.generate_walls()

    def generate_walls(self):
        """Generate basic wall structure"""
        walls = set()
        width = self.game_state.width   # Get from game_state
        height = self.game_state.height # Get from game_state
        
        # Border walls
        for x in range(width):
            walls.add((x, 0))
            walls.add((x, height - 1))
        for y in range(height):
            walls.add((0, y))
            walls.add((width - 1, y))
        
        # Internal walls (every other position)
        for x in range(2, width - 2, 2):
            for y in range(2, height - 2, 2):
                walls.add((x, y))
        
        return walls
    
    async def handle_client(self, websocket):
        player_id = f"player_{self.next_player_id}"
        self.next_player_id += 1
        self.clients[websocket] = player_id
        
        # Add player to game (starting position)
        self.game_state.players[player_id] = {"x": 1, "y": 1}
        
        print(f"{player_id} connected")
        
        try:
            # Send initial game state
            await websocket.send(json.dumps({
                "type": "init",
                "player_id": player_id,
                "state": self.game_state.to_dict()
            }))
            
            # Handle messages from client
            async for message in websocket:
                await self.handle_message(websocket, message)
        
        except websockets.exceptions.ConnectionClosed:
            print(f"{player_id} disconnected")
        finally:
            # Remove player on disconnect
            if player_id in self.game_state.players:
                del self.game_state.players[player_id]
            del self.clients[websocket]
    
    async def handle_message(self, websocket, message):
        data = json.loads(message)
        player_id = self.clients[websocket]
        
        if data["type"] == "move":
            self.handle_move(player_id, data["direction"])
        
        elif data["type"] == "place_bomb":
            self.handle_place_bomb(player_id)
        
        # Broadcast updated state to all clients
        await self.broadcast_state()
    
    def handle_move(self, player_id, direction):
        player = self.game_state.players[player_id]
        new_x, new_y = player["x"], player["y"]
        
        if direction == "up":
            new_y -= 1
        elif direction == "down":
            new_y += 1
        elif direction == "left":
            new_x -= 1
        elif direction == "right":
            new_x += 1
        
        # Check collision with walls
        if (new_x, new_y) not in self.game_state.walls:
            player["x"] = new_x
            player["y"] = new_y
    
    def handle_place_bomb(self, player_id):
        player = self.game_state.players[player_id]
        bomb = {
            "x": player["x"],
            "y": player["y"],
            "timer": 3.0,  # 3 seconds
            "owner_id": player_id
        }
        self.game_state.bombs.append(bomb)
        print(f"{player_id} placed bomb at ({player['x']}, {player['y']})")
    
    async def broadcast_state(self):
        if not self.clients:
            return
        
        message = json.dumps({
            "type": "state_update",
            "state": self.game_state.to_dict()
        })
        
        await asyncio.gather(
            *[client.send(message) for client in self.clients.keys()],
            return_exceptions=True
        )
    
    async def game_loop(self):
        """Update bomb timers periodically"""
        while True:
            await asyncio.sleep(0.1)  # Update 10 times per second
            
            # Update bomb timers
            for bomb in self.game_state.bombs[:]:
                bomb["timer"] -= 0.1
                if bomb["timer"] <= 0:
                    self.game_state.bombs.remove(bomb)
                    print(f"Bomb exploded at ({bomb['x']}, {bomb['y']})")
            
            if self.clients:
                await self.broadcast_state()

async def main():
    server = GameServer()
    
    # Start game loop
    asyncio.create_task(server.game_loop())
    
    # Start WebSocket server
    async with websockets.serve(server.handle_client, "localhost", 8765):
        print("Server started on ws://localhost:8765")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())