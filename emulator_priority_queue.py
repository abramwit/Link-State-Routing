

class EmulatorPriorityQueue:

    def __init__(self):
        self.priority_queue = []

    def __heapify(self):
        # Sort the priority in descending order by the cost to get to the emulator
        self.priority_queue.sort(key=lambda x: x.get_cost(), reverse=True)
    
    def insert(self, emulator):
        self.priority_queue.append(emulator)
        self.__heapify()

    def get_min(self):
        # If empty return None
        if not self.priority_queue:
            return
        # If not empty return
        else:
            return self.priority_queue.pop()
    
    def is_not_empty(self):
        if self.priority_queue == []:
            return False
        return True