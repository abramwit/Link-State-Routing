import argparse
import ipaddress
import socket
import logging
import struct
import datetime


class LinkStateProtocol:

    def __init__(self, emulator):
        self.emulator_obj = emulator
        self.forwarding_tbl = []
        self.neighbor_nodes = []
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
                for node in self.neighbor_nodes:
                    # logging.debug("Sending hello packet to [ip:port] -- " + node['ip'] + " : " + str(node['port']))
                    self.emulator_obj.get_sock().sendto(self.emulator_obj.assemblepacket('H', 1, [node['ip'], node['port']], -1), (node['ip'],
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
                    lsp, lsp_header, neighbors = self.emulator_obj.deassemblepacket(lsp)

                    if lsp_header[4][0] == drop_node['ip'] and lsp_header[4][1] == drop_node['port']:
                        self.cur_LSP.remove(lsp)

            if len(neighbor_timeout) >= 1:
                for node in self.neighbor_nodes:
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
                    for neighbor in self.neighbor_nodes:
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
            for neighbor in self.neighbor_nodes:
                if not (neighbor["ip"].__eq__(new_header[4][0]) and neighbor["port"] == new_header[4][1]):
                    # logging.debug("Forwarding new LSP to node at " + neighbor['ip'] + " : " +
                    #               str(neighbor['port']))
                    self.emulator_obj.get_sock().sendto(new_lsp, (neighbor["ip"], neighbor["port"]))

        return

    def buildforwardingtable(self):
        confirmed = [{"dest": [self.emulator_obj.get_ip(), self.emulator_obj.get_port()], "cost": 0, "next_hop": None}]
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
    

