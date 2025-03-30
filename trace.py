import argparse
import ipaddress
import socket
import logging
import struct
import datetime


class Trace:
    routetrace_addr = [-1, -1]  # route trace  addr in the form [IP addr, port #]
    src_addr = [-1, -1]
    dest_addr = [-1, -1]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    debug = 0

    def parse(self):
        # Parse command line args
        parser = argparse.ArgumentParser()
        parser.add_argument('-a', '--routetrace_port', type=int, help='the port that the routetrace listens on for '
                                                                      'incoming packets')
        parser.add_argument('-b', '--src_hostname', help='the src hostname to send packets to')
        parser.add_argument('-c', '--src_port', help='the src port to send packets to')
        parser.add_argument('-d', '--dest_hostname', help='the dest hostname to send packets to')
        parser.add_argument('-e', '--dest_port', help='the dest port to send packets to')
        parser.add_argument('-f', '--debug', type=int, help='1: print out information, 0: do not print information')
        args = parser.parse_args()

        # Set up logging
        logging.basicConfig(level=logging.DEBUG)

        # Set routetrace address and socket
        self.routetrace_addr = [socket.gethostbyname(socket.gethostname()), int(args.routetrace_port)]
        self.src_addr = [socket.gethostbyname(args.src_hostname), int(args.src_port)]
        self.dest_addr = [socket.gethostbyname(args.dest_hostname), int(args.dest_port)]

        # Code used when testing routetrace address and socket
        # self.routetrace_addr = ['127.0.0.1', int(args.routetrace_port)]
        # self.src_addr = ['127.0.0.1', int(args.src_port)]
        # self.dest_addr = ['127.0.0.1', int(args.dest_port)]

        self.debug = args.debug
        self.sock.bind((self.routetrace_addr[0], int(self.routetrace_addr[1])))

    def routetrace(self):
        TTL = 0

        print("Hop # IP Port")
        self.sock.sendto(self.assemblepacket('T', TTL, self.dest_addr, -1),
                         (self.src_addr[0], int(self.src_addr[1])))

        while True:
            # Receive packets from other nodes
            packet, addr = self.sock.recvfrom(1024)
            packet, header, data = self.deassemblepacket(packet)

            if self.debug == 1:
                print(str(TTL+1) + " " + header[4][0] + "," + str(header[4][1]))

            # Trace packet reached destination
            if header[4][0].__eq__(self.dest_addr[0]) and header[4][1] == self.dest_addr[1]:
                return

            # Trace packed did not reach destination
            else:
                TTL += 1
                self.sock.sendto(self.assemblepacket('T', TTL, self.dest_addr, -1),
                                 (self.src_addr[0], int(self.src_addr[1])))

        pass

    def assemblepacket(self, p_type, ttl, dest, ack_seq_no):
        # Packet layout
        # - packet_type (L: Link State Packet, H: Hello Message, A: Acknowledgement, ...)
        # TODO: what to set TTL to? Set to 10 for now

        # Encode IP addresses
        src_ip = int(ipaddress.IPv4Address(self.routetrace_addr[0]))
        dest_ip = int(ipaddress.IPv4Address(dest[0]))

        # Route trace packet
        if p_type == 'T':
            # Construct acknowledgement packet, increment sequence number and append list of neighbors
            trace_pkt = struct.pack("!cIIIIIII", p_type.encode(), 0, 0, ttl, src_ip, int(self.routetrace_addr[1]),
                              dest_ip, int(self.dest_addr[1]))

            return trace_pkt

        else:
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

        return packet, header, data


trace = Trace()

trace.parse()

trace.routetrace()
