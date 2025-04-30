# config.py

# ===================
# Network & Bootstrap
# ===================
BOOTSTRAP_NODE = "127.0.0.1:8000"  # Format: host:port
GOSSIP_FANOUT = 3                  # Number of random targets per gossip round

# ==============
# Gossip Timing
# ==============
HEARTBEAT_INTERVAL = 1             # Heartbeat increases every second
GOSSIP_INTERVAL = 2                # Send gossip every T seconds
FAILURE_TIMEOUT = 10               # Time after which a node is suspected if no response
FAILURE_HARD_DEAD = 15             # Time after which a node is declared dead

# ===================
# Consistent Hashing
# ===================
VIRTUAL_NODE_REPLICAS = 100        # Number of virtual nodes per physical node
