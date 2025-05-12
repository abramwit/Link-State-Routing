#--------------------------------------------------------------------------------------------------------------------------------------------------------#
#                                                                   IMPORTS                                                                              #
#--------------------------------------------------------------------------------------------------------------------------------------------------------#

import argparse
import ipaddress
import socket
import logging
import struct
import datetime
import time

from link_state_routing import LinkStateProtocol

#--------------------------------------------------------------------------------------------------------------------------------------------------------#
#                                                                   ENUMERATIONS                                                                         #
#--------------------------------------------------------------------------------------------------------------------------------------------------------#

# Recieve Packet Enums
NR_BYTES_ACCEPTED = 1024

# Packet Header Enums - The value corresponds to what index in the packet the information is retrieved from
P_HEADER_LEN = 29 # Note: packet header is 29 chars
P_HEADER_TYPE = 0
P_HEADER_ID = 1
P_HEADER_SEQ_NR = 2
P_HEADER_TTL = 3 # Note: TTL = Time to Live (each time a packet is passed to a new address the TTL is decremented, this prevents immortal packets)
P_HEADER_SRC_HOST = 4 # Note: when using deassembled packet header src address is accessed as {src_hostname, src_port}
P_HEADER_SRC_PORT = 5
P_HEADER_DEST_HOST = 6 # Note: when using deassembled packet header src address is accessed as {dest_hostname, dest_port}
P_HEADER_DEST_PORT = 7

# Packet Creation Enums - The values used to assemble the default trace packet
TRACE_PACKET_TYPE = "T"
ACKNOWLEDGE_PACKET_TYPE = "A"
LSP_PACKET_TYPE = "L"
HELLO_PACKET_TYPE = "H"
DEFAULT_ID = 0
DEFAULT_SEQ_NR = 0
DEFAULT_TRACE_TTL = 0 # Note: trace packets use TTL of 0 and increment on each 'hop' (movement from one address to another) to track how many 'hops' are made

# Access Packet Enums - The values used to access the deassembled packet
P_TYPE = 0
P_ID = 1
P_SEQ_NR = 2
P_TTL = 3
P_SRC_ADDR = 4
P_DEST_ADDR = 5
HOST = 0
PORT = 1

#--------------------------------------------------------------------------------------------------------------------------------------------------------#
#                                                                   CLASSES / FUNCTIONS                                                                  #
#--------------------------------------------------------------------------------------------------------------------------------------------------------#

class EmulatorInProgress:

    def __init__(self, existing_emulator=False, ip='0.0.0.0', port=-1, neighbors=[], cost=0, tracer=False):
        # Parse command line args
        parser = argparse.ArgumentParser()
        parser.add_argument('-p', '--port', type=int, help='the port that the emulator listens on for incoming packets')
        parser.add_argument('-f', '--filename', help='the name of the topology file described above')
        args = parser.parse_args()

        # Set up logging
        logging.basicConfig(level=logging.DEBUG)

        self.lsp = None

        if not existing_emulator:
            self.ip = socket.gethostbyname(socket.gethostname())
            self.port = int(args.port)
            time.sleep(2)
            self.id, self.neighbors = self.__readtopology(args.filename)
            self.cost = 0
            self.seq_no = 0
            self.tracer = tracer

            # Set emulator address and socket while testing - keep commented in production
            # self.emulator_addr = ['127.0.0.1', int(args.port)]

            # Set emulator address and socket
            # TODO: Do this as part of separate method so I can create Emulator objects from link_state_routing.py
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.get_ip(), self.get_port()))
            self.sock.setblocking(False)
        
        else:
            self.ip = ip
            self.port = int(port)
            self.id = -1
            self.neighbors = neighbors
            self.cost = cost
            self.seq_no = 0
            self.tracer = tracer

    
    def __readtopology(self, filename):
        try:
            emulator_id = -1
            neighbors = []
            
            file = open(filename, 'r').read().splitlines()

            # Read through lines of topology.txt
            for entry in file:

                if not entry:
                    return -1, []

                emulator_id += 1
                ft = entry.split()

                # If nodes [IP addr, port #] matches first [IP addr, port #] in line, match found
                if socket.gethostbyname(ft[0].split(',')[0]).__eq__(self.get_ip()) and int(ft[0].split(',')[1]) == self.get_port():
                    # Copy nodes direct neighbors to neighbor_nodes
                    for node in ft[1:]:
                        node = node.split(',')
                        neighbors.append({'ip': socket.gethostbyname(node[0]), 'port': int(node[1]), 'last_hello': -1})

                    return emulator_id, neighbors

        except FileNotFoundError:
            logging.warning('Topology file not found')
            exit(-1)
    

    def get_ip(self):
        return self.ip
    

    def set_ip(self, ip):
        self.ip = ip
    

    def get_port(self):
        return self.port
    

    def set_port(self, port):
        self.port = port
    

    def __get_id(self):
        return self.id


    def get_neighbors(self):
        return self.neighbors
    

    def set_neighbors(self, neighbors):
        self.neighbors = neighbors

    
    def append_neighbor(self, neighbor):
        self.neighbors.append(neighbor)
    

    def remove_neighbor(self, neighbor):
        self.neighbors.remove(neighbor)


    def get_cost(self):
        return self.cost
    

    def set_cost(self, cost):
        self.cost = cost
    
    
    def get_seq_no(self):
        return self.seq_no
    

    def increment_seq_no(self):
        self.seq_no += 1

    
    def get_sock(self):
        return self.sock
    


    def assemblepacket(self, p_type, ttl, dest, ack_seq_no, trace_addr=[]):
        # Packet layout
        # Packet layout
        # - packet_type (L: Link State Packet, T: Trace Packet, H: Hello Message, A: Acknowledgement)
        # - packet_id   (For now using default ID of 0)
        # - packet_seq_nr (# packet in the sequence i.e. if 3 packets are sent there are seq. #'s 0, 1 and 2)
        # - TTL         (Packet's time to live - prevent immortal packets)
        # - src_address_ip (source addresses IP/Host)
        # - src_address_port (source addresses port)
        # - dest_address_ip (dest. addresses IP/Host)
        # - dest_address_port (dest. addresses port)

        # TODO: what to set TTL to? Set to 10 for now

        # Encode IP addresses
        src_ip = int(ipaddress.IPv4Address(self.get_ip()))
        src_port = self.get_port()
        dest_ip = int(ipaddress.IPv4Address(dest[HOST]))
        dest_port = dest[PORT]

        # Link State Packet (LSP)
        if p_type == LSP_PACKET_TYPE:

            # Turn list of neighbor nodes into string (data) of neighbor nodes
            data = ""
            for neighbor in self.get_neighbors():
                data += str(neighbor["ip"]) + "," + str(neighbor["port"]) + " "

            # Construct LSP, increment sequence number and append list of neighbors
            lsp_pkt = struct.pack("!cIIIIIII", 
                                  LSP_PACKET_TYPE.encode(), 
                                  self.__get_id(), 
                                  self.get_seq_no(), 
                                  ttl, 
                                  src_ip, 
                                  src_port,
                                  dest_ip, 
                                  dest_port)
            
            # Increment sequence number
            self.increment_seq_no()

            # Append list of neighbor nodes to LSP packet
            lsp_pkt += str(data).encode()
            return lsp_pkt

        # Hello Packet
        elif p_type == HELLO_PACKET_TYPE:

            # Construct Hello Packet
            hello_pkt = struct.pack("!cIIIIIII", 
                                    HELLO_PACKET_TYPE.encode(), 
                                    self.__get_id(), 
                                    self.get_seq_no(), 
                                    ttl, 
                                    src_ip,
                                    src_port, 
                                    dest_ip, 
                                    dest_port)

            return hello_pkt

        # Acknowledgement Packet
        elif p_type == ACKNOWLEDGE_PACKET_TYPE:

            # Construct Acknowledgement Packet
            ack_pkt = struct.pack("!cIIIIIII", 
                                  ACKNOWLEDGE_PACKET_TYPE.encode(), 
                                  self.__get_id(), 
                                  ack_seq_no, 
                                  ttl, 
                                  src_ip,
                                  src_port, 
                                  dest_ip, 
                                  dest_port)

            return ack_pkt
        
        # Route Trace Packet
        if p_type == TRACE_PACKET_TYPE:

            # Construct acknowledgement packet, increment sequence number and append list of neighbors
            trace_ip = int(ipaddress.IPv4Address(trace_addr[0]))
            trace_port = int(trace_addr[PORT])

            # Construct Route Trace Packet
            trace_pkt = struct.pack("!cIIIIIII",
                                    TRACE_PACKET_TYPE.encode(),
                                    DEFAULT_ID,
                                    DEFAULT_SEQ_NR,
                                    0,
                                    trace_ip,
                                    trace_port,
                                    dest_ip, 
                                    dest_port)

            return trace_pkt

        else:
            # If Packet Type is unknown, then log warning
            logging.warning("Assemble payload called with unknown packet type.")

        return
    

    def deassemblepacket(self, packet):
        header = struct.unpack("!cIIIIIII", packet[:29])
        data = packet[29:].decode()

        # Unpack packet header
        p_type = header[0].decode()
        p_ID = header[1]
        p_seq_no = header[2]
        TTL = header[3]
        src_addr = [socket.inet_ntoa(struct.pack('!L', header[4])), header[5]]
        dest_addr = [socket.inet_ntoa(struct.pack('!L', header[6])), header[7]]
        header = [p_type, p_ID, p_seq_no, TTL, src_addr, dest_addr]

        # If LSP packet, reconstruct senders neighbor list from encoded appended data
        if p_type == 'L':
            sender_neighbors = []
            data = data.split()

            for entry in data:
                entry = entry.split(',')
                sender_neighbors.append({'ip': entry[0], 'port': int(entry[1])})

            return packet, header, sender_neighbors

        # If Trace Route packet
        elif p_type == 'T':

            if not self.tracer:
                self.forwardtracepacket(src_addr, TTL, dest_addr)

        return packet, header, data


    def forwardtracepacket(self, trace_addr, TTL, dest_addr):

        forwarding_tbl = self.lsp.get_forwarding_tbl()

        # Send packet back to trace addr acknowleding packet was recieved and is on it's way to the next hop
        trace_pkt = self.assemblepacket('A', TTL, trace_addr, 0)
        self.sock.sendto(trace_pkt, (trace_addr[0], trace_addr[1]))

        # If trace packet has reached destination stop forwarding trace packet
        if dest_addr[0].__eq__(self.get_ip()) and dest_addr[1] == self.get_port():
            return

        # Else, look in forwarding table for next hop on way to destination
        for entry in forwarding_tbl.get_values():

            if dest_addr[0].__eq__(entry.get_ip()) and dest_addr[1] == entry.get_port():
                TTL -= 1
                trace_pkt = self.assemblepacket('T', TTL, dest_addr, 0, trace_addr)
                next_ip, next_port = entry.get_next_hop()
                self.sock.sendto(trace_pkt, (next_ip, next_port))


if __name__ == '__main__':
    emulator = EmulatorInProgress()

    emulator.lsp = LinkStateProtocol(emulator)

    emulator.lsp.createroutes()