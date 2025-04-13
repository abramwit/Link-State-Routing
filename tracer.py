import argparse
import ipaddress
import socket
import logging
import struct
import datetime

from emulator import EmulatorInProgress

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
TRACE_PACKET = "T"
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

DEBUG_MODE = 1

class Trace(EmulatorInProgress):
    routetrace_addr = [-1, -1]  # route trace  addr in the form [IP addr, port #]
    src_addr = [-1, -1]
    dest_addr = [-1, -1]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    debug = 0

    def __init__(self):
        # Parse command line args
        parser = argparse.ArgumentParser()
        # TODO: SET PORT AND IP USING EMULATOR CLASS THAT WE ARE INHERITING AND MAKE COMMON PACKET ASSEMBLE / DEASSEMBLE IN EMULATOR
        parser.add_argument('-p', '--routetrace_port', type=int, help='the port that the routetrace listens on for '
                                                                      'incoming packets')
        parser.add_argument('-sh', '--src_hostname', help='the src hostname to send packets to')
        parser.add_argument('-sp', '--src_port', help='the src port to send packets to')
        parser.add_argument('-dh', '--dest_hostname', help='the dest hostname to send packets to')
        parser.add_argument('-dp', '--dest_port', help='the dest port to send packets to')
        parser.add_argument('-d', '--debug', type=int, help='1: print out information, 0: do not print information')
        args = parser.parse_args()

        # Set up logging
        logging.basicConfig(level=logging.DEBUG)

        # Set routetrace address and socket --- TODO: uncomment testing lines
        # self.routetrace_addr = ['127.0.0.1', int(args.routetrace_port)]                             # TODO - comment
        self.routetrace_addr = [socket.gethostbyname(socket.gethostname()), int(args.routetrace_port)]   # TODO - uncomment
        # self.src_addr = ['127.0.0.1', int(args.src_port)]                             # TODO - comment
        self.src_addr = [socket.gethostbyname(args.src_hostname), int(args.src_port)]   # TODO - uncomment
        # self.dest_addr = ['127.0.0.1', int(args.dest_port)]                             # TODO - comment
        self.dest_addr = [socket.gethostbyname(args.dest_hostname), int(args.dest_port)]   # TODO - uncomment

        self.debug = args.debug
        self.sock.bind((self.routetrace_addr[0], int(self.routetrace_addr[1])))

    def routetrace(self):

        hop = 1

        # Output debug table headers
        if self.debug == DEBUG_MODE:
            print("Hop # IP Port")

        # Send first trace packet from routetrace address to the source address
        self.sock.sendto(self.assemblepacket(TRACE_PACKET, 
                                             DEFAULT_TRACE_TTL, 
                                             self.routetrace_addr),
                         (self.src_addr[HOST], int(self.src_addr[PORT])))

        while True:
            # Receive packets from other nodes
            packet, addr = self.sock.recvfrom(NR_BYTES_ACCEPTED)
            packet, header, _ = self.deassemblepacket(packet)

            if self.debug == DEBUG_MODE:
                print(str(hop) + " " + header[4][HOST] + "," + str(header[4][PORT]))
                hop += 1

            # Trace packet reached destination
            if (header[P_SRC_ADDR][HOST].__eq__(self.dest_addr[HOST])) and (header[P_SRC_ADDR][PORT] == self.dest_addr[PORT]):
                return

            # Trace packed did not reach destination
            # else:
            #     TTL += 1
            #     self.sock.sendto(self.assemblepacket('T', 
            #                                          TTL, 
            #                                          self.dest_addr),
            #                      (self.src_addr[0], int(self.src_addr[1])))

        pass

    def assemblepacket(self, p_type, ttl, ack_seq_no = -1):
        # Packet layout
        # - packet_type (L: Link State Packet, T: Trace Packet... in future could add H: Hello Message, A: Acknowledgement)
        # - packet_id   (For now using default ID of 0)
        # - packet_seq_nr (# packet in the sequence i.e. if 3 packets are sent there are seq. #'s 0, 1 and 2)
        # - TTL         (Packet's time to live - prevent immortal packets)
        # - src_address_ip (source addresses IP/Host)
        # - src_address_port (source addresses port)
        # - src_address_ip (source addresses IP/Host)
        # - src_address_port (source addresses port)

        # Encode IP addresses
        trace_ip = int(ipaddress.IPv4Address(self.routetrace_addr[HOST]))
        dest_ip = int(ipaddress.IPv4Address(self.dest_addr[HOST]))

        # Route trace packet
        if p_type == TRACE_PACKET:
            # Construct acknowledgement packet, increment sequence number and append list of neighbors
            trace_pkt = struct.pack("!cIIIIIII",
                                    TRACE_PACKET.encode(),
                                    DEFAULT_ID,
                                    DEFAULT_SEQ_NR,
                                    ttl,
                                    trace_ip,
                                    int(self.routetrace_addr[PORT]),
                                    dest_ip, 
                                    int(self.dest_addr[PORT]))

            return trace_pkt

        else:
            logging.warning("Assemble payload called with unknown packet type.")

        return

    def deassemblepacket(self, packet):
        header = struct.unpack("!cIIIIIII", packet[:P_HEADER_LEN])
        data = packet[P_HEADER_LEN:].decode()

        # Unpack packet header
        p_type = header[P_HEADER_TYPE].decode()
        p_ID = header[P_HEADER_ID]
        p_seq_nr = header[P_HEADER_SEQ_NR]
        TTL = header[P_HEADER_TTL]
        src_addr = [socket.inet_ntoa(struct.pack('!L', header[P_HEADER_SRC_HOST])), header[P_HEADER_SRC_PORT]]
        dest_addr = [socket.inet_ntoa(struct.pack('!L', header[P_HEADER_DEST_HOST])), header[P_HEADER_DEST_PORT]]
        header = [p_type, p_ID, p_seq_nr, TTL, src_addr, dest_addr]

        return packet, header, data


trace = Trace()

trace.routetrace()
