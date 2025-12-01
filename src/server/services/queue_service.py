import heapq

class EventQueue:
    def __init__(self):
        self.heap = []

    def push(self, execute_tick, event, data):
        heapq.heappush(self.heap, (execute_tick, event, data))

    def pop_ready(self, current_tick):
        ready = []
        while self.heap and self.heap[0][0] <= current_tick:
            ready.append(heapq.heappop(self.heap))
        return ready