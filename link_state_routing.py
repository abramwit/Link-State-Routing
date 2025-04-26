import argparse
import ipaddress
import socket
import logging
import struct
import datetime

from emulator_priority_queue import EmulatorPriorityQueue
from emulator import EmulatorInProgress

class ForwardingTableEntry():
    
    def __init__(self, emulator, next_hop, in_spf):
        self.emulator = emulator
        self.next_hop = next_hop
        self.in_spf = in_spf

    def get_entry(self):
        return self.emulator, self.next_hop, self.in_spf
    
    def get_next_hop(self):
        return self.next_hop
    
    def update_next_hop(self, new_next_hop):
        self.next_hop = new_next_hop

    def set_in_spf(self, in_spf):
        self.in_spf = in_spf

    def get_in_spf(self):
        return self.in_spf


class ForwardingTable(ForwardingTableEntry):

    def __init__(self):
        # EMULATOR   NEXT-HOP   IN-SPF
        self.forwarding_table = []


    def __get_emulator_key(self, emulator):
        key = str(emulator.get_ip()) + ',' + str(emulator.get_port())
        return key
    
    
    def __get_forwarding_table(self):
        return self.forwarding_table
    

    def __get_entry(self, emulator):
        key = self.__get_emulator_key(emulator)

        for entry in self.__get_forwarding_table():
            if list(entry.keys())[0] == key:
                return entry[self.__get_emulator_key(emulator)]
        return False

    
    def add_entry(self, emulator, next_hop):
        key = self.__get_emulator_key(emulator)
        entry = ForwardingTableEntry(emulator, next_hop, False)
        self.forwarding_table.append({key:entry})

    
    def get_next_hop(self, emulator):
        entry = self.__get_entry(emulator)
        if entry:
            return entry.get_next_hop()
        else:
            raise Exception('Exception in get_next_hop function - entry not found!')


    def update_next_hop(self, emulator, new_next_hop):
        entry = self.__get_entry(emulator)
        if entry:
            entry.update_next_hop(new_next_hop)
        else:
            raise Exception('Exception in update_next_hop function - entry not found!')


    def find_next_hop(self, starting, predecessor, destination):
        # If starting node == predecessor node, then go to destination. The destination is the 'next-hop'.
        if starting == predecessor:
            return destination
        
        # Find forwarding table entry who's next-node equals the current next-node (starting with predecessor)
        for entry in self.__get_forwarding_table():
            start_node, next_node, _ = entry.values()[0].get_entry()
            if start_node == predecessor:
                # Return the starting_node
                return next_node
        
        # If next-hop not found raise an error
        raise Exception('Exception in is_emulator_in_spf_tree function - entry not found!')


    def is_emulator_in_forwarding_table(self, emulator):
        in_table = self.__get_entry(emulator)
        if in_table:
            return True
        return False


    def is_emulator_in_spf_tree(self, emulator):
        # Status of whether emulator is in the shortest path tree
        entry = self.__get_entry(emulator)
        if entry:
            return entry.get_in_spf()
        else:
            raise Exception('Exception in is_emulator_in_spf_tree function - entry not found!')


    def add_emulator_to_sp_tree(self, emulator):
        # Add emulator to the shortest path tree
        entry = self.__get_entry(emulator)
        if entry:
            entry.set_in_spf(True)
        else:
            raise Exception('Exception in add_emulator_to_sp_tree function - entry not found!')


class LinkStateProtocol:

    def __init__(self, emulator):
        self.emulator_obj = emulator
        self.forwarding_tbl = []
        self.cur_LSP = []  # Up-to-date Link State Packet


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
        confirmed = [{"dest": [self.emulator_obj.get_ip(), self.emulator_obj.get_port()], "cost": 0, "next_hop": None}]
        tentative = []
        in_algo = False

        ### TEST

        # Create Forwarding Table w/ Destination, In SPF?, Cost and  Next Hop
        forwarding_table = ForwardingTable()

        # Create an Empty Priority Queue
        priority_queue = EmulatorPriorityQueue()

        # Set the cost of the starting emulator to 0 in the Forwarding Table
        forwarding_table.add_entry(self.emulator_obj, self.emulator_obj)

        # Insert the starting emulator into the priority queue and set it's cost to 0
        priority_queue.insert(self.emulator_obj)

        # While the priority queue is not empty
        while priority_queue:

            # Get the emulator from the priority queue with the minimum cost
            emulator = priority_queue.get_min()

            # If the emulator is not in the forwarding tables SPF tree
            if not forwarding_table.is_emulator_in_spf_tree(emulator):

                # Insert the node into the forwarding table and set it's status in the SPF tree to True
                forwarding_table.add_emulator_to_sp_tree(emulator)

                # For all of the added emulator's neighbors
                for neighbor in emulator.get_neighbors():

                    # Calculate the cost to the neighbor [cost = weight(u,v) + table[v].cost]
                    new_cost = 1 + emulator.get_cost()

                    # If the forwarding table does not have a cost for the neighbor or the calculated cost is lower
                    if not forwarding_table.is_emulator_in_forwarding_table(neighbor) or (neighbor.get_cost > new_cost):

                        # Insert the neighbor into the forwarding table (set it's cost and 'next hop')
                        neighbor.set_cost(new_cost)
                        next_hop = forwarding_table(emulator)

                        if not forwarding_table.is_emulator_in_forwarding_table(neighbor):
                            forwarding_table.add_entry(neighbor, next_hop)

                        else:
                            forwarding_table.update_next_hop(neighbor, next_hop)

                        # Insert the neighbor and it's cost into the priority queue
                        priority_queue.insert(neighbor)

        ### TEST

        # Consider all neighbor nodes of this emulator
        for neighbor in self.emulator_obj.get_neighbors():
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
            if not (entry["dest"][0].__eq__(self.emulator_obj.get_ip()) and entry["dest"][1] == self.emulator_obj.get_port()):
                print(entry["dest"][0] + "," + str(entry["dest"][1]) + " " +
                      entry["next_hop"][0] + "," + str(entry["next_hop"][1]))
        print()

    def getnodesneighbors(self, node):
        # Returns a given nodes neighbors
        for lsp in self.cur_LSP:
            lsp, lsp_header, neighbors = self.emulator_obj.deassemblepacket(lsp)

            if node['dest'][0] == lsp_header[4][0] and node['dest'][1] == lsp_header[4][1]:
                return neighbors

        return []
    

