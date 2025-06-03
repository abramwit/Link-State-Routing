
![lsp_demo](https://github.com/user-attachments/assets/267fe11b-b04b-42c0-b032-8f08c7cd2bff)

# Link State Protocol (LSP) Network Emulator. 
The Python-based repository allows the operator to define a custom network topology, simulate link-state routing, and trace the path taken between emulated network nodes.

Link-State Protocol is a type of dynamic routing protocol used in computer networks to determine the best paths for data packets to travel. Unlike distance-vector protocols that share their entire routing tables with directly connected neighbors, link-state protocols work by having each router acquire a complete understanding of the network's topology.

## ✨Features
* Define a custom network topology using configuration files
* Simulate Link State Protocol behavior
* Run multiple emulators to act as routers/nodes
* Dynamically calculate shortest paths using Dijkstra’s algorithm
* Trace packet route taken between any two emulators with a tracer script

## 📁 Project Structure

link_state_emulator/
├── emulators/
│   ├── emulator.py         # Core emulator logic for each node
├── topology/
│   ├── topology_config.json # Defines the network topology
├── tracer/
│   ├── trace.py            # Script to trace hops between nodes
├── utils/
│   ├── graph_utils.py      # Graph handling and shortest path logic
├── main.py                 # Entrypoint to start the emulation
├── README.md


## 🚀 Getting Started

Requirements
	•	Python 3.8+
	•	networkx for graph operations
	•	matplotlib (optional) for visualizing the topology

### Install dependencies:

pip install -r requirements.txt

Define Your Topology

Create a topology_config.json file:

{
  "nodes": ["A", "B", "C", "D"],
  "links": [
    {"from": "A", "to": "B", "cost": 1},
    {"from": "B", "to": "C", "cost": 2},
    {"from": "C", "to": "D", "cost": 1},
    {"from": "A", "to": "D", "cost": 5}
  ]
}

### Run the Emulation

python main.py --topology topology/topology_config.json

Each emulator will simulate a router that exchanges link state information and builds its own routing table.

### Trace a Path

To trace the hop-by-hop path from one emulator to another:

python tracer/trace.py --src A --dst D

Sample output:

Tracing route from A to D:
A -> B -> C -> D
Total cost: 4

## 🧠 Here is how the Link-State Protocol works:
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

## Here are the key characteristics and Advantages of Link-State Protocols:
1.  Complete Network Picture: Routers have a full understanding of the network topology, leading to more intelligent routing decisions.
2. Fast Convergence: When a change occurs in the network (e.g., a link goes down), only specific LSAs related to that change are flooded, allowing for rapid updates and faster convergence (the time it takes for all routers to agree on the new network state).
3. Loop-Free Paths: The use of shortest-path algorithms inherently prevents routing loops, a common problem with distance-vector protocols.
4. Scalability: They are well-suited for larger and more complex networks because they don't suffer from the "count-to-infinity" problem that affects distance-vector protocols.
5. Triggered Updates: Updates are only sent when there's a change in the network, reducing unnecessary network overhead compared to periodic full routing table broadcasts.

## Future Improvements
* Support for dynamic link failures and updates
* Allow router link “costs” to be set


# Link State Routing

Implemented link-state routing (LSR) protocol to determine the shortest path between a fixed, known set of nodes.

Implemented the "reliable flooding" algorithm where each node communicates only with it's neighbors to learn the topology.

The topology.txt file plans the topology. Each node will read only their line of the topology.txt file to learn it's immediate neighbors. Each node will then send "Hello" and "Link State" messages to 

Designed nodes in the LSR protocol to reconfigure paths and stabilize in a fixed time period when the  topology changes due to nodes being created or going down.

## Description

An in-depth paragraph about your project and overview of use.

## Getting Started

### Dependencies

* Describe any prerequisites, libraries, OS version, etc., needed before installing program.
* ex. Windows 10

### Installing

* How/where to download your program
* Any modifications needed to be made to files/folders
```
code blocks for commands
```

### Executing program

* How to run the program
* Step-by-step bullets
```
code blocks for commands
```

## Help

Any advise for common problems or issues.
```
command to run if program contains helper info
```

## Authors

Contributors names and contact info

ex. Dominique Pizzie  
ex. [@DomPizzie](https://twitter.com/dompizzie)

## Version History

* 0.2
    * Various bug fixes and optimizations
    * See [commit change]() or See [release history]()
* 0.1
    * Initial Release

## License

This project is licensed under the [NAME HERE] License - see the LICENSE.md file for details
