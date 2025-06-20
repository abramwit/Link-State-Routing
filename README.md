
# Link State Protocol (LSP) Network Emulator. 
This Python-based repository allows the operator to define a custom network topology, simulate link-state routing, and trace the path taken between emulated network nodes.

Link-State Protocol is a type of dynamic routing protocol used in computer networks to determine the best paths for data packets to travel. Unlike distance-vector protocols that share their entire routing tables with directly connected neighbors, link-state protocols work by having each router acquire a complete understanding of the network's topology.

## Project Demo

### Live Demo
![lsp_demo](https://github.com/user-attachments/assets/267fe11b-b04b-42c0-b032-8f08c7cd2bff)

### Demo Explanation
<img src="demo/Link State Routing GitHub Portfolio Project Demo Slide 1.png" width="560" height="315">
<img src="demo/Link State Routing GitHub Portfolio Project Demo Slide 2.png" width="560" height="315">
<img src="demo/Link State Routing GitHub Portfolio Project Demo Slide 3.png" width="560" height="315">

## How does Link-State-Routing work?
1. Neighbor Discovery: When a router starts, it first discovers its directly connected neighbors by sending out "hello" packets.
2. Link-State Advertisements (LSAs): Each router then creates a special packet called a Link-State Packet. A Link-State Packet contains information about:
    - The router's own identity.
    - It’s directly connected links.
    - The "cost" of each link (e.g., bandwidth, delay, reliability). In this repository we set all link costs to 1 for simplicity.
    - The state of those links (up or down).
3. Link-State Packet Flooding: These Link-State Packets are then "flooded" throughout the entire network. This means every router receives a copy of every other router's Link-State Packet. Crucially, Link-State Packet are forwarded without modification. Link-State Packets are assigned a time-to-live (TTL) so they are not forwarded indefinitely. Each router assigns an ID to its Link-State Packets so other routers can track the latest version.
4. Link-State Database: Each router collects all the received Link-State Packets and compiles them into a Link-State Database. This database provides a comprehensive "map" or graph of the entire network topology, showing all routers and their interconnections.
5. Shortest Path Calculation: With the complete network map in its Link-State Database, each router independently uses the Dijkstra shortest-path algorithm to calculate the best, loop-free path to every other destination in the network. The router itself acts as the root of this calculated "shortest path tree."
6. Routing Table Construction: Based on these calculated shortest paths, each router builds its own routing table, which lists the best next hop for every possible destination.

## Features
* Define a custom network topology using configuration files
* Simulate Link State Protocol behavior
* Run multiple emulators to act as routers/nodes
* Dynamically calculate shortest paths using Dijkstra’s algorithm
* Trace packet route taken between any two emulators with a tracer script

## Getting Started
Requirements
* Python 3

### Clone the Link-State-Routing Repository
Clone this GitHub project repository. One way to do this is listed below:
```
git clone https://github.com/abramwit/Link-State-Routing.git
```

### Define Network Topology
Use the default network topology defined in topology.txt or define your own:

topology.txt is interpreted in the following way (where all source and neighbor emulators should be defined in their own line):

```
<source-ip>,<source-port> <neighbor_a-ip>,<neighbor_a-port> <neighbor_b-ip>,<neighbor_b-port>
```

### Run the Emulators
To invoke all emulators and have them perform the Link-State Protocol run the following command:

```
python3 emulator.py -p <port> -f <topology-filename>
```

Note that each emulator must be set-up in it's own instance of the terminal. This can be performed by re-running the command above in separate terminal tabs.

### Trace the Route taken between running Emulators
tracer.py is an application similar to the standard traceroute tool which will trace the hops along a shortest path between the source and destination emulators.

To trace the hop-by-hop path from the source to destination emulator run the following command once all emulators are set-up and have output their forwarding table:

```
python3 tracer.py -p <tracer-port> -sh <source-emulator-ip> -sp <source-emulator-port> -dh <destination-emulator-ip> -dp <destination-emulator-port> -d 1
```

Sample output:

<pre>
_Hop-#_  _IP,Port_  
   1     127.0.0.1,2051  
   2     127.0.0.1,2052  
   3     127.0.0.1,2054  
   4     127.0.0.1,2055  
</pre>

## Here are the key characteristics and Advantages of Link-State Protocols:
1.  Complete Network Picture: Routers have a full understanding of the network topology, leading to more intelligent routing decisions.
2. Fast Convergence: When a change occurs in the network (e.g., a link goes down), only specific LSAs related to that change are flooded, allowing for rapid updates and faster convergence (the time it takes for all routers to agree on the new network state).
3. Loop-Free Paths: The use of shortest-path algorithms inherently prevents routing loops, a common problem with distance-vector protocols.
4. Scalability: They are well-suited for larger and more complex networks because they don't suffer from the "count-to-infinity" problem that affects distance-vector protocols.
5. Triggered Updates: Updates are only sent when there's a change in the network, reducing unnecessary network overhead compared to periodic full routing table broadcasts.

## Future Improvements
* Support for dynamic link failures and updates
* Allow router link “costs” to be set --> Currently we set all router link costs to 1

## Help
Use the -h flag for more information on the arguments for the emulator.py and tracer.py files. 

