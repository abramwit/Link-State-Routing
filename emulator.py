import argparse
import ipaddress
import socket
import logging
import struct
import datetime


class Emulator:
    emulator_addr = [-1, -1]  # Emulator node addr in the form [IP addr, port #]
    forwarding_tbl = []
    neighbor_nodes = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ID = 0  # Node ID corresponds to node entry line number in topology.txt
    seq_no = 0  # Sequence # incremented by 1 for each LSP sent, reset to 0 if node goes down
    cur_LSP = []  # Up-to-date Link State Packet

    def parse(self):
        # Parse command line args
        parser = argparse.ArgumentParser()
        parser.add_argument('-p', '--port', type=int, help='the port that the emulator listens on for incoming packets')
        parser.add_argument('-f', '--filename', help='the name of the topology file described above')
        args = parser.parse_args()

        # Set up logging
        logging.basicConfig(level=logging.DEBUG)

        # Set emulator address and socket --- TODO: uncomment testing lines
        self.emulator_addr = ['127.0.0.1', int(args.port)]  # TODO - comment
        # self.emulator_addr = [socket.gethostbyname(socket.gethostname()), args.port]      # TODO - uncomment
        self.sock.bind((self.emulator_addr[0], int(self.emulator_addr[1])))
        self.sock.setblocking(False)

        # Read topology and set up forwarding table
        self.readtopology(args.filename)

    def readtopology(self, filename):
        try:
            file = open(filename, 'r').read().splitlines()

            # Read through lines of topology.txt
            for entry in file:
                self.ID += 1
                ft = entry.split()

                # If nodes [IP addr, port #] matches first [IP addr, port #] in line, match found
                if socket.gethostbyname(ft[0].split(',')[0]).__eq__(self.emulator_addr[0]) and int(ft[0].split(',')[1]) == self.emulator_addr[
                    1]:
                    # Copy nodes direct neighbors to neighbor_nodes
                    for node in ft[1:]:
                        node = node.split(',')
                        self.neighbor_nodes.append({'ip': socket.gethostbyname(node[0]), 'port': int(node[1]), 'last_hello': -1})

                    return

        except FileNotFoundError:
            logging.warning('Topology file not found')
            exit(-1)

    def createroutes(self):
        # Implements a link-state routing protocol to set up the shortest path forwarding
        # table between nodes in the specified topology (reliable flooding)

        # Generate new LSP if hello packet not received from neighbor in timeout
        recv_timeout = datetime.timedelta(seconds=2)

        # Send hello messages and LSP to neighbors and continue to send after each send_timeout
        for node in self.neighbor_nodes:
            self.sock.sendto(self.assemblepacket('H', 1, [node['ip'], node['port']], -1), (node['ip'], node['port']))
            self.sock.sendto(self.assemblepacket('L', 10, [node['ip'], node['port']], -1), (node['ip'], node['port']))
            # logging.debug("Sending hello packet and LSP to [ip:port] -- " + node['ip'] + " : " + str(node['port']))
        send_hello = datetime.datetime.now()
        send_timeout = datetime.timedelta(seconds=0.5)

        topography_change = False
        build_ft_timeout = datetime.timedelta(seconds=3)
        build_ft_wait = -1

        while True:
            unavailable = True
            neighbor_timeout = []

            try:
                # Receive packets from other nodes
                packet, addr = self.sock.recvfrom(1024)
                packet, header, data = self.deassemblepacket(packet)

                # Hello packet received from neighbor node
                if header[0] == 'H':
                    # logging.debug("Received hello packet from [ip:port] -- " + header[4][0] + " : " +
                    #               str(header[4][1]))

                    # Check if sender of hello message in neighbor list
                    for node in self.neighbor_nodes:

                        if header[4][0].__eq__(node['ip']) and header[4][1] == node['port']:
                            # Hello message received from previously available neighbor node
                            node['last_hello'] = datetime.datetime.now()
                            unavailable = False

                    # Hello packet received from previously unavailable node, add to neighbors list and generate new LSP
                    if unavailable:
                        # logging.debug('Previously unavailable node with [ip:port] has become available -- ' +
                        #               header[4][0] + ' : ' + str(header[4][1]))
                        self.neighbor_nodes.append({'ip': header[4][0], 'port': header[4][1],
                                                    'last_hello': datetime.datetime.now()})
                        topography_change = True

                        for node in self.neighbor_nodes:
                            # logging.debug("Sending LSP packet to [ip:port] -- " +
                            #               node['ip'] + " : " + str(node['port']))
                            self.sock.sendto(self.assemblepacket('L', 10, [node['ip'], node['port']], -1),
                                             (node['ip'], node['port']))

                # LSP packet received
                elif header[0] == 'L':
                    # logging.debug("Received LSP packet from [ip:port] -- " + header[4][0] + " : " + str(header[4][1]))
                    self.forwardpacket(packet)
                    topography_change = True

                # Route trace packet
                elif header[0] == 'T':
                    pass

                else:
                    logging.warning("Received packet with unknown packet type.")

            except socket.error:
                # For some reason logging line below caused errors in node sending/receiving capabilities...
                # logging.warning('No packets received by node, socket.error raised.')
                pass

            # Send hello packet to all neighbors if send_timeout has passed
            if datetime.datetime.now() - send_hello > send_timeout:
                for node in self.neighbor_nodes:
                    # logging.debug("Sending hello packet to [ip:port] -- " + node['ip'] + " : " + str(node['port']))
                    self.sock.sendto(self.assemblepacket('H', 1, [node['ip'], node['port']], -1), (node['ip'],
                                                                                                   node['port']))

                send_hello = datetime.datetime.now()

            # If hello packet not received in time, remove neighbor and generate new LSP
            for node in self.neighbor_nodes:
                if node['last_hello'] == -1:
                    # Give neighbors leeway on first hello message (set to -1), then store datetime regardless of recv
                    node['last_hello'] = datetime.datetime.now()

                elif datetime.datetime.now() - node['last_hello'] > recv_timeout:
                    # logging.debug('No hello received from [ip:port] in receive timeout -- ' + node['ip'] + " : " +
                    #               str(node['port']))
                    neighbor_timeout.append(node)
                    topography_change = True

            for drop_node in neighbor_timeout:
                # logging.debug('Removing [ip:port] from neighbor nodes list -- ' + drop_node['ip'] + " : " +
                #               str(drop_node['port']))
                self.neighbor_nodes.remove(drop_node)

                # When dropping neighbor node also remove LSP entry
                for lsp in self.cur_LSP:
                    lsp, lsp_header, neighbors = self.deassemblepacket(lsp)

                    if lsp_header[4][0] == drop_node['ip'] and lsp_header[4][1] == drop_node['port']:
                        self.cur_LSP.remove(lsp)

            if len(neighbor_timeout) >= 1:
                for node in self.neighbor_nodes:
                    # logging.debug("Sending LSP packet to [ip:port] -- " + node['ip'] + " : " + str(node['port']))
                    self.sock.sendto(self.assemblepacket('L', 10, [node['ip'], node['port']], -1),
                                     (node['ip'], node['port']))

            # If there is a change in topography rebuild forwarding table
            if topography_change:
                build_ft_wait = datetime.datetime.now()
                topography_change = False

            if (build_ft_wait != -1) and datetime.datetime.now() - build_ft_wait > build_ft_timeout:
                build_ft_wait = -1
                self.buildforwardingtable()

    def assemblepacket(self, p_type, ttl, dest, ack_seq_no, trace_addr=[]):
        # Packet layout
        # - packet_type (L: Link State Packet, H: Hello Message, A: Acknowledgement, ...)
        # TODO: what to set TTL to? Set to 10 for now

        # Encode IP addresses
        src_ip = int(ipaddress.IPv4Address(self.emulator_addr[0]))
        dest_ip = int(ipaddress.IPv4Address(dest[0]))

        # Link State Packet (LSP)
        if p_type == 'L':
            # Change neighbor node list to string
            data = ""
            for neighbor in self.neighbor_nodes:
                data += str(neighbor["ip"]) + "," + str(neighbor["port"]) + " "

            # Construct LSP, increment sequence number and append list of neighbors
            LSP = struct.pack("!cIIIIIII", p_type.encode(), self.ID, self.seq_no, ttl, src_ip, self.emulator_addr[1],
                              dest_ip, dest[1])
            self.seq_no += 1

            return LSP + str(data).encode()

        elif p_type == 'H':
            # Construct hello packet, increment sequence number and append list of neighbors
            hello_pkt = struct.pack("!cIIIIIII", p_type.encode(), self.ID, self.seq_no, ttl, src_ip,
                                    self.emulator_addr[1], dest_ip, dest[1])

            return hello_pkt

        # TODO: don't think I'll use
        elif p_type == 'A':
            # Construct acknowledgement packet, increment sequence number and append list of neighbors
            ack_pkt = struct.pack("!cIIIIIII", p_type.encode(), self.ID, ack_seq_no, ttl, src_ip,
                                  self.emulator_addr[1], dest_ip, dest[1])

            return ack_pkt

        # Route trace packet
        if p_type == 'T':
            src_ip = int(ipaddress.IPv4Address(trace_addr[0]))

            # Construct acknowledgement packet, increment sequence number and append list of neighbors
            trace_pkt = struct.pack("!cIIIIIII", p_type.encode(), 0, 0, ttl, src_ip, trace_addr[1],
                                    dest_ip, dest[1])

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
        header = [p_type, p_ID, p_seq_no, TTL, src_addr]

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
            # If TTL equals 0 then modify packet, replace src address with emulators and send back to trace
            if TTL == 0:
                trace_pkt = self.assemblepacket('T', TTL, src_addr, 0, self.emulator_addr)
                self.sock.sendto(trace_pkt, (src_addr[0], src_addr[1]))

            # If TTL is not 0, decrement TTL and send packet on next hop to destination
            else:
                for dest in self.forwarding_tbl:
                    if dest_addr[0].__eq__(dest["dest"][0]) and dest_addr[1] == dest["dest"][1]:
                        TTL -= 1
                        trace_pkt = self.assemblepacket('T', TTL, dest_addr, 0, src_addr)
                        self.sock.sendto(trace_pkt, (dest['next_hop'][0], dest['next_hop'][1]))

        return packet, header, data

    def forwardpacket(self, packet):
        no_lsp_for_id = True
        new_lsp, new_header, new_data = self.deassemblepacket(packet)

        # If node does have an LSP from ID replace if sequence number greater than currently stored LSP
        for lsp in self.cur_LSP:
            cur_lsp, cur_header, cur_data = self.deassemblepacket(lsp)

            if cur_header[1] == new_header[1]:
                no_lsp_for_id = False

                if new_header[2] > cur_header[2]:
                    # logging.debug("Received LSP with greater sequence number from node " + str(cur_header[1]) +
                    #               " at address " + cur_header[4][0] + " : " + str(cur_header[4][1]))
                    # logging.info(new_data)
                    self.cur_LSP.remove(cur_lsp)
                    self.cur_LSP.append(new_lsp)

                    # Forward Up-to-date LSP to all neighbors except the node LSP was received from
                    for neighbor in self.neighbor_nodes:
                        if not (neighbor["ip"].__eq__(new_header[4][0]) and neighbor["port"] == new_header[4][1]):
                            # logging.debug("Forwarding updated LSP to node at " + neighbor['ip'] + " : " +
                            #               str(neighbor['port']))
                            self.sock.sendto(new_lsp, (neighbor["ip"], neighbor["port"]))

                    return

        # If node does not have an LSP for given sender ID then store
        if no_lsp_for_id:
            # logging.debug("Received new LSP from node " + str(new_header[1]) + " at address " +
            #               new_header[4][0] + " : " + str(new_header[4][1]))
            # logging.info(new_data)
            self.cur_LSP.append(new_lsp)

            # Forward new LSP to all neighbors except the node LSP was received from
            for neighbor in self.neighbor_nodes:
                if not (neighbor["ip"].__eq__(new_header[4][0]) and neighbor["port"] == new_header[4][1]):
                    # logging.debug("Forwarding new LSP to node at " + neighbor['ip'] + " : " +
                    #               str(neighbor['port']))
                    self.sock.sendto(new_lsp, (neighbor["ip"], neighbor["port"]))

        return

    def buildforwardingtable(self):
        confirmed = [{"dest": self.emulator_addr, "cost": 0, "next_hop": None}]
        tentative = []
        in_algo = False

        # Consider all neighbor nodes of this emulator
        for neighbor in self.neighbor_nodes:
            tentative.append({"dest": [neighbor["ip"], neighbor["port"]], "cost": 1, "next_hop": [neighbor["ip"], neighbor["port"]]})

        # While all nodes have not been attached by Dijkstra consider next node
        while len(tentative) != 0:
            w = tentative[0]
            confirmed.append(w)
            tentative.remove(w)

            # Update tentative list with node w's neighbors, keep the lowest cost path
            w_neighbors = self.getnodesneighbors(w)

            for neighbor in w_neighbors:
                in_algo = False

                # If neighbor already in tentative list replace if new path is lower
                for dest in tentative:
                    if neighbor['ip'] == dest['dest'][0] and neighbor['port'] == dest['dest'][1]:
                        in_algo = True

                        if dest['cost'] > (w['cost'] + 1):
                            dest['cost'] = (w['cost'] + 1)
                            dest['next_hop'] = w['dest']

                # If neighbor already in confirmed then ignore
                for dest in confirmed:
                    if neighbor['ip'] == dest['dest'][0] and neighbor['port'] == dest['dest'][1]:
                        in_algo = True

                if not in_algo:
                    tentative.append({"dest": [neighbor["ip"], neighbor["port"]], "cost": (w['cost'] + 1), "next_hop": [w["dest"][0], w["dest"][1]]})

        self.forwarding_tbl = confirmed

        # Print Forwarding Table
        # logging.info(str(self.forwarding_tbl))
        print("Forwarding Table:")
        for entry in self.forwarding_tbl:
            if not (entry["dest"][0].__eq__(self.emulator_addr[0]) and entry["dest"][1] == self.emulator_addr[1]):
                print(entry["dest"][0] + "," + str(entry["dest"][1]) + " " +
                      entry["next_hop"][0] + "," + str(entry["next_hop"][1]))
        print()

    def getnodesneighbors(self, node):
        # Returns a given nodes neighbors
        for lsp in self.cur_LSP:
            lsp, lsp_header, neighbors = self.deassemblepacket(lsp)

            if node['dest'][0] == lsp_header[4][0] and node['dest'][1] == lsp_header[4][1]:
                return neighbors

        return []


emulator = Emulator()

emulator.parse()

emulator.createroutes()
