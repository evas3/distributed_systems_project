import time
from queue import Queue
from services.comms import ClientComms
import threading

class ServerLoop:
    def __init__(self, tick_rate=60):
        self.tick_rate = tick_rate
        self.global_tick = 0
        self.tick_interval = 1.0 / tick_rate

        self.client_queues = {}

        self.comms = ClientComms()

        self.wait_for_clients()
        self.last_tick = time.perf_counter()


    def start_loop(self):
        while True:
            now = time.perf_counter()

            if now - self.last_tick >= self.tick_interval:
                self.global_tick += 1
                self.last_tick += self.tick_interval

                self.process_inputs()
                #update state
                #send updates to clients

            time.sleep(0.0005)
    
    def process_inputs(self):
        for client, q in self.client_queues.items():
            while not q.empty():
                msg = q.get()
                print(msg)
                self.handle_input(client, msg)

    def handle_input(self, client, msg):
        print(msg["event_type"], flush=True)

    def wait_for_clients(self):
        #TODO make into a loop for more clients
        client_socket = self.comms.receive_connection()

        client_q = Queue()
        self.client_queues[client_socket] = client_q

        thread = threading.Thread(
            target=self.comms.handle,
            args=(client_socket, client_q),
            daemon=True
        )

        thread.start()