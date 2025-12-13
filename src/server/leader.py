import time
import json
import threading
from queue import Queue
from services.comms import ClientComms
from services.queue_service import EventQueue
from objects.bomb import BombObject
from objects.explosion import ExplosionObject
import socket



class Leader:
    def __init__(self, server_loop):
        self.server_loop = server_loop

        self.client_queues = {}
        my_config = self.server_loop.peers_config[self.server_loop.server_id-1]
        self.comms = ClientComms(my_config[1], my_config[2])
        
        self.follower_sockets = {}
        self.follower_queues = {}

        self.client_sockets = []
        self.outgoing_events = []
        self.last_tick = time.perf_counter()
        self.comms.start_listening()
        accept_thread = threading.Thread(target=self.accept_clients, daemon=True)
        accept_thread.start()

    def run(self):

        self.last_tick = time.perf_counter()
        
        while True:
            now = time.perf_counter()
            if now - self.last_tick >= self.server_loop.tick_interval:
                self.server_loop.global_tick += 1
                self.last_tick += self.server_loop.tick_interval

                while not self.server_loop.peer_queue.empty():
                    msg = self.server_loop.peer_queue.get()
                    print(msg, flush=True)
                    if msg["type"] == "leader_announce":
                        if msg["from"] < self.server_loop.server_id:
                            return "DEMOTION"
                        else:
                            self.server_loop.send_leader_announce()
                    elif msg["type"] == "bully_ok":
                        pass
                    elif msg["type"] == "bully":
                        pass

                if self.server_loop.global_tick % 60 == 0:
                    print(f"[LEADER] Global Tick: {self.server_loop.global_tick}", flush=True)

                if self.server_loop.global_tick % 50 == 0:
                    self.send_clock_sync()

                if self.server_loop.global_tick - self.server_loop.last_heartbeat_sent >= self.server_loop.heartbeat_interval:
                    self.send_heartbeat()
                    self.server_loop.last_heartbeat_sent = self.server_loop.global_tick

                self.outgoing_events = []


                self.leader_process_inputs()
                self.leader_handle_events()
                self.broadcast_state()

            time.sleep(0.0005)


    def accept_clients(self):
        while True:
            try:
                sock = self.comms.receive_connection()
                if not sock:
                    continue
                
                print(f"[NET] Accepted new connection", flush=True)

                try:
                    raw = sock.recv(1024).decode("utf-8")
                    handshake = json.loads(raw)
                except:
                    print("[NET] Invalid handshake, closing socket", flush=True)
                    sock.close()
                    continue
                
                msg_type = handshake.get("type")

                if msg_type == "client_hello":
                    print("[NET] Connection identified as CLIENT", flush=True)
                    self.client_sockets.append(sock)

                    client_q = Queue()
                    self.client_queues[sock] = client_q
                    
                    thread = threading.Thread(
                        target=self.comms.handle,
                        args=(sock, client_q),
                        daemon=True
                    )
                    thread.start()
                    
                    if self.server_loop.new_player_id <= 4: 
                        self.server_loop.new_player_id += 1

                elif msg_type == "server_hello":
                    print(f"[NET] Connection identified as FOLLOWER SERVER", flush=True)

                    server_id = handshake.get("server_id")
                    self.follower_sockets[server_id] = sock

                    self.follower_queues[server_id] = Queue()

                    thread = threading.Thread(
                        target=self.comms.handle_follower,
                        args=(sock, self.follower_queues[server_id]),
                        daemon=True
                    )
                    thread.start()

                else:
                    print(f"[NET] Unknown handshake type: {msg_type}", flush=True)
                    sock.close()

            except Exception as e:
                print(f"[NET] Accept error: {e}", flush=True)
                break

    def send_heartbeat(self):
        msg = {
            "type": "heartbeat",
            "leader_id": self.server_loop.server_id,
            "tick": self.server_loop.global_tick
        }
        raw = json.dumps(msg).encode("utf-8")
        dropped = []
        for follower_id, follower_sock in self.follower_sockets.items():
            try:
                follower_sock.sendall(raw)
            except:
                print("[LEADER] Lost follower during heartbeat!", flush=True)
                try:
                    follower_sock.shutdown(socket.SHUT_RDWR)
                except:
                    pass

                try:
                    follower_sock.close()
                except:
                    pass

                dropped.append(follower_id)
        if dropped:
            for follower_id in dropped:
                del self.follower_sockets[follower_id]

    def send_clock_sync(self):
        tick = self.server_loop.global_tick
        timestamp = time.perf_counter()
        print(f"[CLOCK] Syncing clients to tick {tick}", flush=True)
        self.comms.broadcast(self.client_sockets, "clock", {"server_tick": tick, "timestamp": timestamp}, tick)

    def send_event_to_followers(self, event):
        msg = {"type": "event", "event": event}
        raw = json.dumps(msg).encode()
        for sock in self.follower_sockets.values():
            sock.sendall(raw)

    def broadcast_state(self):
        if len(self.outgoing_events) == 0:
            return
        
        for sock in self.follower_sockets.values():
            try:
                self.comms.broadcast([sock], "event", self.outgoing_events, self.server_loop.global_tick)
            except:
                print("[NET] Follower disconnected during broadcast of event", flush=True)
                #TODO DELETE DISCONNECTED FOLLOWERS
        if not self.wait_for_acks(self.server_loop.global_tick):
            self.broadcast_state()
            return
        
        for sock in self.follower_sockets.values():
            try:
                self.comms.broadcast([sock], "commit", [], self.server_loop.global_tick)
            except Exception as e:
                print(f"[NET] Follower disconnected during broadcast of commit: {e}", flush=True)
                #TODO DELETE DISCONNECTED FOLLOWERS
        
        active_sockets = []
        for sock in self.client_sockets:
            try:
                self.comms.broadcast([sock], "update", self.outgoing_events, self.server_loop.global_tick)
                active_sockets.append(sock)
            except:
                print("[NET] Client disconnected during broadcast", flush=True)
                if sock in self.client_queues:
                    del self.client_queues[sock]
        
        self.client_sockets = active_sockets

    def wait_for_acks(self, tick):
        #TODO ADD TIMEOUT
        while self.comms.acks < len(self.follower_sockets):
            time.sleep(0.0005)
            continue
        if self.comms.acks == len(self.follower_sockets):
            self.comms.acks = 0
            return True

    def leader_process_inputs(self):
        for client, q in self.client_queues.items():
            while not q.empty():
                msg = q.get()
                print(f"[INPUT] Received {msg['event_type']} from client", flush=True)
                self.leader_handle_input(client, msg)

    def leader_handle_input(self, client, msg):
        self.leader_parse_event(msg["event_type"], msg["data"])

    def leader_handle_events(self):
        ready = self.server_loop.event_queue.pop_ready(self.server_loop.global_tick)
        for event in ready:
            self.leader_parse_event(event[1], event[2])


    def leader_parse_event(self, event_type, event_data):
        # 0 = bomb spawn
        # 1 = bomb explode
        # 2 = player moves
        # 3 = remove explosion
        # 4 = player stops moving
        match event_type:
            case 0:
                self.leader_spawn_bomb(event_data)
            case 1:
                self.leader_explode_bomb(event_data)
            case 2:
                self.leader_move_player(event_data)
            case 3:
                self.leader_remove_explosion(event_data[0], event_data[1], event_data[2])
            case 4:
                self.leader_finish_moving(event_data)

    def leader_spawn_bomb(self, data):
        x, y = data[0], data[1]
        if self.server_loop.bomb_map[y][x] != 0:
            return
        bomb_id = self.server_loop.global_bomb_id
        owner = data[2]
        self.server_loop.bombs[bomb_id] = BombObject(bomb_id, x, y, owner)
        self.server_loop.bomb_map[y][x] = bomb_id
        explode_tick = self.server_loop.global_tick + 120
        self.server_loop.event_queue.push(explode_tick, 1, bomb_id)
        self.outgoing_events.append({"event_type": 0, "data": [x, y, bomb_id, owner, explode_tick]})
        self.server_loop.global_bomb_id += 1

    def leader_explode_bomb(self, data):
        bomb_id = data
        if self.server_loop.bombs.get(bomb_id) is None:
            #already exploded
            return
        x, y, owner = self.server_loop.bombs[bomb_id].x, self.server_loop.bombs[bomb_id].y, self.server_loop.bombs[bomb_id].owner
        self.server_loop.bomb_map[y][x] = 0
        del self.server_loop.bombs[bomb_id]
        self.leader_spawn_explosion(x, y, owner)
        for direction in [(1,0), (-1,0), (0,1), (0,-1)]:
            nx = x + direction[0]
            ny = y + direction[1]
            if nx < 0 or nx > len(self.server_loop.level_map[0]) - 1 or ny < 0 or ny > len(self.server_loop.level_map) - 1:
                continue
            if self.server_loop.level_map[ny][nx] != 0:
                continue
            self.leader_spawn_explosion(nx, ny, owner)
            if self.server_loop.bomb_map[ny][nx] != 0:
                chain_bomb_id = self.server_loop.bomb_map[ny][nx]
                self.server_loop.event_queue.push(self.server_loop.global_tick, 1, chain_bomb_id)
                self.outgoing_events.append({"event_type": 0, "data": [nx, ny, chain_bomb_id, self.server_loop.bombs[chain_bomb_id].owner, self.server_loop.global_tick]})
                continue

    def leader_spawn_explosion(self, x, y, owner):
        new_explosion = ExplosionObject(x, y, owner)
        self.server_loop.explosion_map[y][x] += 1
        self.server_loop.explosions[self.server_loop.global_explosion_id] = new_explosion
        self.server_loop.event_queue.push(self.server_loop.global_tick + 90, 3, (self.server_loop.global_explosion_id, x, y))
        self.server_loop.global_explosion_id += 1

    def leader_remove_explosion(self, id, x, y):
        """removes given explosion object"""
        self.server_loop.explosion_map[y][x] -= 1
        del self.server_loop.explosions[id]

    def leader_move_player(self, data):
        player_id, x, y = data[0], data[1], data[2]
        player_x = self.server_loop.players[player_id].x
        player_y = self.server_loop.players[player_id].y
        new_x = player_x + x
        new_y = player_y + y
        if self.server_loop.players[player_id].moving:
            return
        if (0 <= new_x < len(self.server_loop.level_map[0])) and (0 <= new_y < len(self.server_loop.level_map)):
            if self.server_loop.level_map[new_y][new_x] != 0:
                return
            elif self.server_loop.player_map[new_y][new_x] != 0:
                return
            elif self.server_loop.bomb_map[new_y][new_x] != 0:
                return
            else:
                self.server_loop.player_map[player_y][player_x] = 0
                self.server_loop.player_map[new_y][new_x] = player_id
                self.server_loop.players[player_id].move(x, y)
                self.outgoing_events.append({"event_type": 2, "data": [player_id, x, y, new_x, new_y]})
                self.server_loop.event_queue.push(self.server_loop.global_tick + 20, 4, player_id)
        else:
            return

    def leader_finish_moving(self, data):
        player_id = data
        self.server_loop.players[player_id].moving = False
        self.outgoing_events.append({"event_type": 4, "data": [player_id]})