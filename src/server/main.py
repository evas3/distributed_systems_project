import sys
from server_loop import ServerLoop

PEERS_CONFIG = [
    (1, "127.0.0.1", 55533),
    (2, "127.0.0.1", 55534),
    (3, "127.0.0.1", 55535)
]

PEER_COMMS_CONFIG = [
    (1, "127.0.0.1", 55536),
    (2, "127.0.0.1", 55537),
    (3, "127.0.0.1", 55538)
]

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

def main():
    server_id = 1
    if len(sys.argv) > 1:
        try:
            server_id = int(sys.argv[1])
        except ValueError:
            print("Invalid server ID, defaulting to 1")

    if server_id < 1 or server_id > len(PEERS_CONFIG):
        print(f"Server ID {server_id} is out of range. Check PEERS_CONFIG.")
        return

    print(f"Initializing Server {server_id}...")
    server = ServerLoop(server_id, PEERS_CONFIG, PEER_COMMS_CONFIG, LEVEL_MAP, PLAYER_MAP, BOMB_MAP, EXPLOSION_MAP)
    server.start()

if __name__ == "__main__":
    main()
