# Multiplayer Play

## Future Phase: LAN Multiplayer & Auto-Discovery
* **Discovery Protocol:** Use an isolated background thread running a native Python `socket` UDP broadcast (`SO_BROADCAST`) on a dedicated port to automatically advertise and detect active games on the same subnet.
* **Network Decoupling Rule:** The local player entity state must be designed to cleanly serialize its position, movement vector, and current action state into a lightweight JSON string or byte struct. 
* **Engine Constraint:** The main single-player game loop must treat the host's world as the "authoritative state." When a client joins, their local engine suspends local world updates and renders positions received via TCP streams.
