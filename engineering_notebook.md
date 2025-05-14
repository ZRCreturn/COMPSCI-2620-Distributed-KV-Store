# Engineering Notebook
# Part one
## 1. Project Initialization

* **Goal:** Build a decentralized, sharded key-value store demonstrating core distributed-systems concepts.
* **Repo structure:**

  * `node.py`: server process (FastAPI)
  * `client.py`: SmartClient REPL
  * `routing_table.py`: consistent-hashing ring
  * `gossip.py`: peer-to-peer membership
  * `data_migrator.py`: background rebalancer
  * `config.py`: tunable parameters
  * `utils.py`: helper functions

## 2. Design Decisions

### 2.1 Consistent Hashing & Virtual Nodes

* **Why:** Minimize key remapping on scale events; balance load across heterogeneous nodes.
* **Implementation:** SHA-256 → 64-bit ring; `VIRTUAL_NODE_REPLICAS=100` per physical host.
* **Trade-offs:** More virtual nodes smooth hotspots but increase metadata size and join latency.

### 2.2 Gossip Protocol

* **Why decentralized membership**, no single point of failure, eventual consistency for cluster view.
* **Mechanism:** Periodic heartbeats + random fan-out of metadata (versioned routing table + heartbeat counters).
* **Failure detection:** timeout (`FAILURE_TIMEOUT`) marks SUSPECT; `FAILURE_HARD_DEAD` marks DEAD and triggers `remove_node`.

### 2.3 Data Migration

* **Why:** On membership changes, keys must move to new owners.
* **Mechanism:** `DataMigrator` monitors `routing_table.version` and streams keys via HTTP PUT.
* **Locking:** coarse-grained lock on migration loop to avoid races with concurrent version bumps.

### 2.4 Client-Side Routing (SmartClient)

* **Why:** Offload routing logic from a centralized proxy; clients track ring and request directly.
* **Versioning:** Clients include `Routing-Version` header; servers respond with updated table when stale.

## 3. Implementation Walkthrough

### 3.1 `routing_table.py`

* **`RoutingTable.add_node`**: inserts 100 `VirtualNode` entries, increments `version`, updates `uid`.
* **`get_responsible_node(key)`**: binary-search on sorted vnode list, wrap around.
* **Serialization**: outputs `nodes`, `version`, `uid` for gossip.

### 3.2 `gossip.py`

* **`heartbeat_map` & `last_seen`**: track counters and timestamps per node.
* **`_gossip_loop`**: select `GOSSIP_FANOUT` peers, POST local state to `/gossip`.
* **`receive_gossip`**: merge heartbeat > local; replace/merge routing table by version and `uid`.
* **Failure detection**: mark dead nodes and call `routing_table.remove_node`, triggering migration.

### 3.3 `data_migrator.py`

* Polls every 5s; if `routing_table.version` changes, identifies obsolete keys and re-PUTs them to new owners.
* Deletes local copy on success.
* **Improvements:** Add exponential backoff on failures; batch migrations; idempotent retries.

### 3.4 `node.py`

* **FastAPI** endpoints for `/kv`, `/join`, `/gossip`, `/routing_table`.
* **Startup**: instantiate `RoutingTable`, start `GossipManager` and `DataMigrator`, bootstrap join.
* **Request logic**: check if responsible; HTTP 403 if not; include routing updates in responses.

### 3.5 `client.py`

* **Bootstrap** from `BOOTSTRAP_NODE`, fetch initial ring.
* **Commands**: `put`, `get`, `show_ring`, `refresh`, `exit`.
* **\_check\_routing\_update**: update local table on version out-of-date.

## 4. Challenges & Resolutions

* **Thread safety:** protected gossip and migration maps with locks; potential finer-grained locks in future.
* **Routing skews:** tunable virtual-node count; future: weighted vnode assignments.
* **Network partitions:** eventual consistency; future: implement vector clocks or Merkle-tree reconciliation for data repair.

## 5. Future Work

* Multi-region awareness: rack/datacenter metadata, latency-aware routing.
* Configurable consistency levels per operation (strong vs. eventual).
* Monitoring dashboard: expose metrics via Prometheus, Grafana.
* Automated chaos testing for resilience verification.

# ******************************************************************

# Part Two 

## Week of April 20–27: Building a Distributed Key-Value Store

### ✅ Overview

This project aimed to build a scalable and decentralized key-value store inspired by systems like Amazon Dynamo and Cassandra. Over the course of a week, I implemented:

- Consistent Hashing with virtual nodes
- Smart clients capable of intelligent routing
- Gossip-based routing table synchronization
- Automatic node join mechanism
- Data migration upon node addition
- Console-based smart client with ring visualization

This notebook documents the design decisions, challenges, and solutions during development.

---

### 🧱 April 20–21: System Architecture and Consistent Hashing

I began by outlining the system architecture. Each node would:

- Host its own key-value storage in memory
- Communicate via HTTP
- Join or leave the network dynamically
- Share a consistent view of the hash ring via gossip

To distribute keys, I implemented **consistent hashing** where each node is hashed onto a 64-bit ring based on its `host:port`. Clients and nodes use the same hashing logic to locate responsible nodes for each key.

The initial `RoutingTable` class supported:
- Adding/removing nodes
- Serializing the table for transmission
- Binary search for key ownership

To address data skew with a small number of nodes, I added **virtual nodes**. Each physical node is represented by 100 virtual nodes spaced randomly around the ring.

---

### 🌐 April 22–24: Gossip Protocol and Version Resolution

A key challenge was achieving consistency without a central coordinator. I implemented a **Gossip Protocol**, where each node periodically sends its:

- Local `heartbeat_map` for liveness detection
- Current `routing_table` including its version and a unique `uid`

Every 2 seconds, each node selects up to 3 peers at random and gossips its current state. When a node receives gossip, it:

1. Updates heartbeat information
2. Compares `routing_table` versions:
   - If remote version is newer → replace
   - If same version but different UID → trigger a merge
   - If older → ignore

This design guarantees eventual consistency while allowing concurrent joins.

---

### 🚀 April 25: Smart Client with Autonomous Routing

I developed a console-based smart client to issue `PUT` and `GET` requests. The client:

- Loads the latest `routing_table` from a bootstrap node
- Reuses the same `RoutingTable` class as the server
- Resolves the responsible node for each key locally
- Sends the request directly to the target node

It also includes a `show_ring` command that visualizes the hash ring and node layout in ASCII format. The client listens for version updates from responses and upgrades its view automatically.

---

### 🧠 April 26: Decentralized Join and Bootstrap Flow

To support new node initialization without central coordination, I added a bootstrapping protocol:

1. The new node contacts a known bootstrap node via `/routing_table`
2. It selects a random peer from the list and sends a `/join` request
3. That peer adds it to the ring and gossips the updated table

This preserves decentralization by ensuring no node holds special join responsibilities. The new node is quickly propagated via `force_gossip_once()`.

---

### 🔁 April 27: Automatic Data Migration on Expansion

With consistent hashing and dynamic joins, key ownership can change after adding a node. I implemented a `DataMigrator` class that runs on each node and monitors routing table changes.

When a version upgrade is detected, it:
- Scans all local keys
- For each key, re-computes its responsible node
- If the key no longer belongs to the current node, sends it to the correct node via HTTP `PUT`
- Upon success, deletes the key locally

This ensures that the hash ring remains balanced and no key is stored by multiple nodes. It only supports expansion migration, as removal recovery would require replication (planned for later).

---

### ✅ Final Status

| Component                | Status |
|--------------------------|--------|
| Node join + bootstrap    | ✅     |
| Consistent Hashing       | ✅     |
| Virtual Nodes            | ✅     |
| Gossip Protocol          | ✅     |
| Conflict Resolution      | ✅     |
| Smart Client             | ✅     |
| Data Migration (on join) | ✅     |
| Node Removal Migration   | ❌     |
| Replication              | ❌     |

---

### 🎓 Reflections

This project taught me how to:
- Build a decentralized system without coordination
- Implement conflict-resilient gossip propagation
- Migrate data consistently during topology changes
- Separate client/server routing logic via shared code

The design reflects core distributed system principles while remaining minimal and educational. Future extensions could include:

- Multi-replica consistency (N/R/W)
- Graceful removal with migration
- Persistent storage and WAL
- Dashboard or metrics monitoring

