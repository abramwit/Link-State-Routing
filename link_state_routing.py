#--------------------------------------------------------------------------------------------------------------------------------------------------------#
#                                                                   IMPORTS                                                                              #
#--------------------------------------------------------------------------------------------------------------------------------------------------------#

import socket
import logging
import datetime

from emulator_priority_queue import EmulatorPriorityQueue

#--------------------------------------------------------------------------------------------------------------------------------------------------------#
#                                                                   ENUMERATIONS                                                                         #
#--------------------------------------------------------------------------------------------------------------------------------------------------------#


#--------------------------------------------------------------------------------------------------------------------------------------------------------#
#                                                                   CLASSES / FUNCTIONS                                                                  #
#--------------------------------------------------------------------------------------------------------------------------------------------------------#

class ForwardingTableEntry():
    
    def __init__(self, dest_ip, dest_port, next_ip, next_port, in_spf, cost):
        self.dest_ip = dest_ip
        self.dest_port = dest_port
        self.next_ip = next_ip
        self.next_port = next_port
        self.in_spf = in_spf
        self.cost = cost

    def get_entry(self):
        return self.dest_ip, self.dest_port
    
    def get_ip(self):
        return self.dest_ip
    
    def get_port(self):
        return self.dest_port
    
    def get_next_hop(self):
        return self.next_ip, self.next_port
    
    def set_next_hop(self, next_ip, next_port):
        self.next_ip, self.next_port = next_ip, next_port

    def get_in_spf(self):
        return self.in_spf

    def set_in_spf(self, in_spf):
        self.in_spf = in_spf

    def get_cost(self):
        return self.cost
    
    def set_cost(self, cost):
        self.cost = cost


class ForwardingTable(ForwardingTableEntry):

    def __init__(self):
        # EMULATOR   NEXT-HOP   IN-SPF
        self.forwarding_table = {}

    
    def get_values(self):
        return self.forwarding_table.values()

    def print_forwarding_table(self, src_ip, src_port):
        print("      Forwarding Table:      ")
        print(' ____dest____   __next-hop__ ')
        for entry in self.forwarding_table.values():
            dest_ip, dest_port = entry.get_entry()
            if not ((dest_ip == src_ip) and (dest_port == src_port)):
                next_ip, next_port = entry.get_next_hop()
                print("{},{} {},{}".format(dest_ip, dest_port, next_ip, next_port))
        print()

    def __get_emulator_key(self, ip, port):
        key = str(ip) + ',' + str(port)
        return key

    def get_entry(self, ip, port):
        key = self.__get_emulator_key(ip, port)
        entry = self.forwarding_table[key]
        return entry
    
    def add_entry(self, ip, port, next_ip, next_port, cost=0):
        key = self.__get_emulator_key(ip, port)
        entry = ForwardingTableEntry(ip, port, next_ip, next_port, False, cost)
        self.forwarding_table[key] = entry
    
    def get_next_hop(self, ip, port):
        key = self.__get_emulator_key(ip, port)
        entry = self.forwarding_table[key]
        return entry.get_next_hop()

    def update_next_hop(self, ip, port, next_ip, next_port):
        key = self.__get_emulator_key(ip, port)
        entry = self.forwarding_table[key]
        entry.set_next_hop(next_ip, next_port)

    def find_next_hop(self, src_ip, src_port, pre_ip, pre_port, dest_ip, dest_port):
        src_key = self.__get_emulator_key(src_ip, src_port)
        pre_key = self.__get_emulator_key(pre_ip, pre_port)

        # If source node == predecessor node, then destination is the 'next-hop'
        if src_key == pre_key:
            return dest_ip, dest_port
        
        # Find forwarding table entry who's next-node equals the current next-node (starting with predecessor)
        entry = self.forwarding_table[pre_key]
        next_ip, next_port = entry.get_next_hop()
        return next_ip, next_port

    def is_emulator_in_forwarding_table(self, ip, port):
        try:
            _ = self.get_entry(ip, port)
            return True
        except Exception:
            return False

    def is_emulator_in_spf_tree(self, ip, port):
        try:
            entry = self.get_entry(ip, port)
            return entry.get_in_spf()
        except Exception:
            return False

    def add_emulator_to_sp_tree(self, ip, port):
        entry = self.get_entry(ip, port)
        entry.set_in_spf(True)
    
    def set_emulator_cost(self, ip, port, cost):
        entry = self.get_entry(ip, port)
        entry.set_cost(cost)
        
    def get_emulator_cost(self, emulator):
        entry = self.get_entry(emulator)
        return entry.get_cost()


class LinkStateProtocol:

    def __init__(self, emulator):
        self.emulator_obj = emulator
        self.forwarding_tbl = []
        self.cur_LSP = []  # Up-to-date Link State Packet
        self.forwarding_tbl = None
    

    def get_forwarding_tbl(self):
        return self.forwarding_tbl


    def createroutes(self):
        # Implements a link-state routing protocol to set up the shortest path forwarding
        # table between nodes in the specified topology (reliable flooding)

        # Generate new LSP if hello packet not received from neighbor in timeout
        recv_timeout = datetime.timedelta(seconds=2)

        # Send hello messages and LSP to neighbors and continue to send after each send_timeout
        for node in self.emulator_obj.get_neighbors():
            self.emulator_obj.get_sock().sendto(self.emulator_obj.assemblepacket('H', 1, [node['ip'], node['port']], -1), (node['ip'], node['port']))
            self.emulator_obj.get_sock().sendto(self.emulator_obj.assemblepacket('L', 10, [node['ip'], node['port']], -1), (node['ip'], node['port']))
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
                packet, addr = self.emulator_obj.get_sock().recvfrom(1024)
                packet, header, data = self.emulator_obj.deassemblepacket(packet)

                # Hello packet received from neighbor node
                if header[0] == 'H':
                    # logging.debug("Received hello packet from [ip:port] -- " + header[4][0] + " : " +
                    #               str(header[4][1]))

                    # Check if sender of hello message in neighbor list
                    for node in self.emulator_obj.get_neighbors():

                        if header[4][0].__eq__(node['ip']) and header[4][1] == node['port']:
                            # Hello message received from previously available neighbor node
                            node['last_hello'] = datetime.datetime.now()
                            unavailable = False

                    # Hello packet received from previously unavailable node, add to neighbors list and generate new LSP
                    if unavailable:
                        # logging.debug('Previously unavailable node with [ip:port] has become available -- ' +
                        #               header[4][0] + ' : ' + str(header[4][1]))
                        self.emulator_obj.append_neighbor({'ip': header[4][0], 'port': header[4][1],
                                                           'last_hello': datetime.datetime.now()})
                        topography_change = True

                        for node in self.emulator_obj.get_neighbors():
                            # logging.debug("Sending LSP packet to [ip:port] -- " +
                            #               node['ip'] + " : " + str(node['port']))
                            self.emulator_obj.get_sock().sendto(self.emulator_obj.assemblepacket('L', 10, [node['ip'], node['port']], -1),
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
                for node in self.emulator_obj.get_neighbors():
                    # logging.debug("Sending hello packet to [ip:port] -- " + node['ip'] + " : " + str(node['port']))
                    self.emulator_obj.get_sock().sendto(self.emulator_obj.assemblepacket('H', 1, [node['ip'], node['port']], -1), (node['ip'],
                                                                                                   node['port']))

                send_hello = datetime.datetime.now()

            # If hello packet not received in time, remove neighbor and generate new LSP
            for node in self.emulator_obj.get_neighbors():
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
                self.emulator_obj.remove_neighbor(drop_node)

                # When dropping neighbor node also remove LSP entry
                for lsp in self.cur_LSP:
                    lsp, lsp_header, neighbors = self.emulator_obj.deassemblepacket(lsp)

                    if lsp_header[4][0] == drop_node['ip'] and lsp_header[4][1] == drop_node['port']:
                        self.cur_LSP.remove(lsp)

            if len(neighbor_timeout) >= 1:
                for node in self.emulator_obj.get_neighbors():
                    # logging.debug("Sending LSP packet to [ip:port] -- " + node['ip'] + " : " + str(node['port']))
                    self.emulator_obj.get_sock().sendto(self.emulator_obj.assemblepacket('L', 10, [node['ip'], node['port']], -1),
                                     (node['ip'], node['port']))

            # If there is a change in topography rebuild forwarding table
            if topography_change:
                build_ft_wait = datetime.datetime.now()
                topography_change = False

            if (build_ft_wait != -1) and datetime.datetime.now() - build_ft_wait > build_ft_timeout:
                build_ft_wait = -1
                self.buildforwardingtable()
    
    def forwardpacket(self, packet):
        no_lsp_for_id = True
        new_lsp, new_header, new_data = self.emulator_obj.deassemblepacket(packet)

        # If node does have an LSP from ID replace if sequence number greater than currently stored LSP
        for lsp in self.cur_LSP:
            cur_lsp, cur_header, cur_data = self.emulator_obj.deassemblepacket(lsp)

            if cur_header[1] == new_header[1]:
                no_lsp_for_id = False

                if new_header[2] > cur_header[2]:
                    # logging.debug("Received LSP with greater sequence number from node " + str(cur_header[1]) +
                    #               " at address " + cur_header[4][0] + " : " + str(cur_header[4][1]))
                    # logging.info(new_data)
                    self.cur_LSP.remove(cur_lsp)
                    self.cur_LSP.append(new_lsp)

                    # Forward Up-to-date LSP to all neighbors except the node LSP was received from
                    for neighbor in self.emulator_obj.get_neighbors():
                        if not (neighbor["ip"].__eq__(new_header[4][0]) and neighbor["port"] == new_header[4][1]):
                            # logging.debug("Forwarding updated LSP to node at " + neighbor['ip'] + " : " +
                            #               str(neighbor['port']))
                            self.emulator_obj.get_sock().sendto(new_lsp, (neighbor["ip"], neighbor["port"]))

                    return

        # If node does not have an LSP for given sender ID then store
        if no_lsp_for_id:
            # logging.debug("Received new LSP from node " + str(new_header[1]) + " at address " +
            #               new_header[4][0] + " : " + str(new_header[4][1]))
            # logging.info(new_data)
            self.cur_LSP.append(new_lsp)

            # Forward new LSP to all neighbors except the node LSP was received from
            for neighbor in self.emulator_obj.get_neighbors():
                if not (neighbor["ip"].__eq__(new_header[4][0]) and neighbor["port"] == new_header[4][1]):
                    # logging.debug("Forwarding new LSP to node at " + neighbor['ip'] + " : " +
                    #               str(neighbor['port']))
                    self.emulator_obj.get_sock().sendto(new_lsp, (neighbor["ip"], neighbor["port"]))

        return
    

    def buildforwardingtable(self):

        # Create Forwarding Table w/ Destination, In SPF?, Cost and  Next Hop
        forwarding_table = ForwardingTable()

        import pdb; pdb.set_trace()

        # Create an Empty Priority Queue
        priority_queue = EmulatorPriorityQueue()

        # Set the cost of the starting emulator to 0 in the Forwarding Table
        forwarding_table.add_entry(self.emulator_obj.get_ip(), self.emulator_obj.get_port(), self.emulator_obj.get_ip(), self.emulator_obj.get_port())
        entry = forwarding_table.get_entry(self.emulator_obj.get_ip(), self.emulator_obj.get_port())

        # Insert the starting emulator into the priority queue and set it's cost to 0
        priority_queue.insert(entry)

        # While the priority queue is not empty
        while priority_queue.is_not_empty():

            # Get the entry from the priority queue with the minimum cost
            entry = priority_queue.get_min()

            # If the emulator is not in the forwarding tables SPF tree
            if not forwarding_table.is_emulator_in_spf_tree(entry.get_ip(), entry.get_port()):

                # Insert the node into the forwarding table and set it's status in the SPF tree to True
                forwarding_table.add_emulator_to_sp_tree(entry.get_ip(), entry.get_port())

                # For all of the added emulator's neighbors
                for neighbor in self.getnodesneighbors(entry):

                    new_entry = False

                    # Calculate the cost to the neighbor [cost = weight(u,v) + table[v].cost]
                    new_cost = 1 + entry.get_cost()

                    # If the forwarding table does not have a cost for the neighbor or the calculated cost is lower
                    if not forwarding_table.is_emulator_in_forwarding_table(neighbor['ip'], neighbor['port']):
                        forwarding_table.add_entry(neighbor['ip'], neighbor['port'], neighbor['ip'], neighbor['port'])
                        new_entry = True
                    
                    neighbor = forwarding_table.get_entry(neighbor['ip'], neighbor['port'])
                    
                    if new_entry or (neighbor.get_cost() > new_cost):

                        # Set the cost of the neighbor emulator
                        neighbor.set_cost(new_cost)

                        # Find the next-hop on the path from the starting emulator to the neighbor emulator
                        entry_ip, entry_port = entry.get_entry()
                        neighbor_ip, neighbor_port = neighbor.get_entry()
                        next_ip, next_port = forwarding_table.find_next_hop(self.emulator_obj.get_ip(), self.emulator_obj.get_port(), entry_ip, entry_port, neighbor_ip, neighbor_port)

                        # Update the neighbor emulator's next-hop
                        forwarding_table.update_next_hop(neighbor.get_ip(), neighbor.get_port(), next_ip, next_port)

                        # Insert the neighbor and it's cost into the priority queue
                        priority_queue.insert(neighbor)

        # Print Forwarding Table
        # logging.info(str(self.forwarding_tbl))
        forwarding_table.print_forwarding_table(self.emulator_obj.get_ip(), self.emulator_obj.get_port())
        self.forwarding_tbl = forwarding_table


    def getnodesneighbors(self, node):
        # If node equals starting emulator then return neighbors
        if (node.get_ip() == self.emulator_obj.get_ip()) and (node.get_port() == self.emulator_obj.get_port()):
            return self.emulator_obj.get_neighbors()
        
        # Returns a given nodes neighbors
        for lsp in self.cur_LSP:
            lsp, lsp_header, neighbors = self.emulator_obj.deassemblepacket(lsp)

            if node.get_ip() == lsp_header[4][0] and node.get_port() == lsp_header[4][1]:
                return neighbors

        return []
    

