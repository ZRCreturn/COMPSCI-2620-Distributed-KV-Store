import hashlib
from bisect import bisect_right
import uuid
from config import VIRTUAL_NODE_REPLICAS

def hash_str(s):
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest(), 16) % (2 ** 64)


class NodeMeta:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.node_id = f"{host}:{port}"

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "host": self.host,
            "port": self.port
        }


class VirtualNode:
    def __init__(self, vnode_id, physical_node_id):
        self.vnode_id = vnode_id
        self.physical_node_id = physical_node_id
        self.hash = hash_str(vnode_id)

    def to_dict(self):
        return {
            "vnode_id": self.vnode_id,
            "hash": self.hash,
            "physical_node_id": self.physical_node_id
        }


class RoutingTable:
    def __init__(self, self_host, self_port):
        self.version = 1
        self.uid = str(uuid.uuid4())
        self.replica_factor = VIRTUAL_NODE_REPLICAS
        self.virtual_nodes = []
        self.node_map = {}
        self.add_node(self_host, self_port)

    def _sorted_insert(self, vnode):
        idx = bisect_right([n.hash for n in self.virtual_nodes], vnode.hash)
        self.virtual_nodes.insert(idx, vnode)

    def add_node(self, host, port):
        node = NodeMeta(host, port)
        node_id = node.node_id
        if node_id in self.node_map:
            return

        self.node_map[node_id] = node
        for i in range(self.replica_factor):
            vnode_id = f"{node_id}#{i}"
            vnode = VirtualNode(vnode_id, node_id)
            self._sorted_insert(vnode)

        self.version += 1
        self.uid = str(uuid.uuid4())

    def remove_node(self, host, port):
        node_id = f"{host}:{port}"
        if node_id not in self.node_map:
            return

        self.node_map.pop(node_id)
        self.virtual_nodes = [v for v in self.virtual_nodes if v.physical_node_id != node_id]

        self.version += 1
        self.uid = str(uuid.uuid4())

    def get_responsible_node(self, key):
        key_hash = hash_str(key)
        idx = bisect_right([v.hash for v in self.virtual_nodes], key_hash)
        if idx == len(self.virtual_nodes):
            idx = 0
        vnode = self.virtual_nodes[idx]
        physical_id = vnode.physical_node_id
        return self.node_map[physical_id]

    def serialize(self):
        return {
            "version": self.version,
            "uid": self.uid,
            "nodes": [node.to_dict() for node in self.node_map.values()]
        }

    def replace_with(self, remote_rt):
        self.node_map.clear()
        self.virtual_nodes.clear()
        for n in remote_rt.get("nodes", []):
            self.add_node(n["host"], n["port"])

        self.version = remote_rt["version"]
        self.uid = remote_rt["uid"]

    def merge_with(self, remote_rt):
        seen = set(self.node_map.keys())
        changed = False
        for n in remote_rt.get("nodes", []):
            node_id = f"{n['host']}:{n['port']}"
            if node_id not in seen:
                changed = True
                self.add_node(n["host"], n["port"])
                seen.add(node_id)
    
    def debug_print(self):
        print(f"RoutingTable (version {self.version}, uid {self.uid}):")
        for v in self.virtual_nodes:
            print(f" - {v.vnode_id} (hash={v.hash}) -> {v.physical_node_id}")
