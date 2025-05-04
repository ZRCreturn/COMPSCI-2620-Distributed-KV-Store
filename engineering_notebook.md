# Engineering Notebook

## 1. Project Initialization

* **Goal:** Build a decentralized, sharded key-value store demonstrating core distributed-systems concepts.
* **Repo structure:**

  * `node.py`: server process (FastAPI)
  * `client.py`: SmartClient REPL
  * `routing_table.py`: consistent-hashing ring
  * `gossip.py`: peer-to-peer membership
  * `data_migrator.py`: background rebalancer
  * `config.py`: tunable parameters

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

