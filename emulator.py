

class Emulator:

    def __init__(self, ip, port, neighbors=None, cost=0):
        self.ip = ip
        self.port = port
        self.neighbors = neighbors
        self.cost = cost
    
    def get_ip(self):
        return self.ip
    
    def get_port(self):
        return self.port
    
    def get_neighbors(self):
        return self.neighbors
    
    def set_neighbors(self, neighbors):
        self.neighbors = neighbors

    def get_cost(self):
        return self.cost
    
    def set_cost(self, cost):
        self.cost = cost

        # TODO: MAKE COMMON PACKET ASSEMBLE / DEASSEMBLE IN EMULATOR