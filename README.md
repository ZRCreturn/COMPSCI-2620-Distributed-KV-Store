# COMPSCI-2620-Distributed-KV-Store

## Overview

This project implements a fully decentralized, sharded key-value store that supports horizontal scaling, fault tolerance, and low-latency operations by combining consistent hashing, virtual nodes, and gossip-based cluster membership.

## Features

* **Sharding** via consistent hashing with virtual nodes
* **Peer-to-peer** coordination using a gossip protocol for membership and failure detection
* **Dynamic rebalancing** and data migration on node join/leave
* **Quorum-based** reads and writes (configurable consistency)
* **HTTP/gRPC API** for client operations (PUT, GET, DELETE)

## Prerequisites

* Python 3.8 or newer
* `pip` for package management

## Installation

```bash
git clone <repo-url>
cd <repo-root>
pip install -r requirements.txt
```

## Configuration

All tunable parameters live in `config.py`:

* **BOOTSTRAP\_NODE**: seed address for initial join (e.g. "127.0.0.1:8000")
* **VIRTUAL\_NODE\_REPLICAS**: number of virtual nodes per physical node
* **GOSSIP\_FANOUT**, **GOSSIP\_INTERVAL**, **HEARTBEAT\_INTERVAL**: gossip settings
* **FAILURE\_TIMEOUT**, **FAILURE\_HARD\_DEAD**: failure detection timing

## Running the Cluster

1. **Start a bootstrap node**:

   ```bash
   python node.py 127.0.0.1 8000
   ```
2. **Start additional nodes**:

   ```bash
   python node.py 127.0.0.1 8001
   python node.py 127.0.0.1 8002
   # …
   ```

   Each node will automatically join the cluster via the bootstrap seed.

## Running the Client

```bash
python client.py
# In the REPL:
> put mykey somevalue
> get mykey
> show_ring
> refresh
> exit
```

## API Endpoints

* **PUT /kv**: store or update a key-value pair
* **GET /kv?key=<key>**: retrieve a value by key
* **POST /join**: add a new node to the ring
* **POST /gossip**: gossip-based membership update
* **GET /routing\_table**: fetch current routing table (tokens + version)

## Testing

* Unit tests for `routing_table.py`, `gossip.py`, and `data_migrator.py` under `tests/`
* Integration tests: bring up a 3-node cluster and verify PUT/GET semantics under node failures.
* To run all tests and get a coverage report, use
  ```bash
  pytest --cov=. --cov-report=term-missing --cov-report=html
  open htmlcov/index.html
  ```

## Contributing

* Fork the repository and open a pull request
* Follow PEP8 style and include tests for new features

## Poster
* here is link to our poster https://drive.google.com/file/d/1D7CFvo0xePPXTV_7kPAasn-DAQeH_vfW/view?usp=sharing

## License

MIT License
