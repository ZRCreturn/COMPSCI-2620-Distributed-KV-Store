import threading
import time
import random
import requests
from routing_table import RoutingTable
from utils import get_host_port
from config import (
    GOSSIP_FANOUT,
    GOSSIP_INTERVAL,
    HEARTBEAT_INTERVAL,
    FAILURE_HARD_DEAD,
    FAILURE_DETECT_INTERVAL
)

class GossipManager:
    """
    A class for one node that manages gossiping between nodes in the network.
    """
    def __init__(self, self_node_id: str, routing_table: RoutingTable) -> None:
        self.self_node_id = self_node_id
        self.routing_table = routing_table
        self.heartbeat_map = {self_node_id: 0}       # heartbeat map of this node (keep incrementing)
        self.last_seen = {self_node_id: time.time()} # last time we heard alive signal from this node
        self.status_map = {self_node_id: "alive"}    # alive status of this node
        self.lock = threading.Lock()
        self.running = False

    def start(self) -> None:
        """
        Starts the gossip manager.
        """
        self.running = True
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        threading.Thread(target=self._gossip_loop, daemon=True).start()
        threading.Thread(target=self._failure_detector_loop, daemon=True).start()

    def _heartbeat_loop(self) -> None:
        """
        A loop that sends heartbeats to other nodes in the network.
        """
        while self.running:
            with self.lock:
                self.heartbeat_map[self.self_node_id] += 1
                self.last_seen[self.self_node_id] = time.time()
            time.sleep(HEARTBEAT_INTERVAL)

    def _gossip_loop(self) -> None:
        """
        A loop that sends gossip messages to other nodes in the network.
        """
        while self.running:
            peers = [n for n in self.routing_table.node_map.keys() if n != self.self_node_id]
            if peers:
                targets = random.sample(peers, min(GOSSIP_FANOUT, len(peers)))
                self._send_gossip(targets)
            time.sleep(GOSSIP_INTERVAL)

    def _send_gossip(self, targets: list[str]) -> None:
        """
        Sends a gossip message to the given targets.
        """
        with self.lock:
            payload = {
                "sender": self.self_node_id,
                "heartbeat_map": self.heartbeat_map,
                "routing_table": self.routing_table.serialize()
            }
        for target in targets:
            try:
                host, port = get_host_port(target)
                url = f"http://{host}:{port}/gossip"
                requests.post(url, json=payload, timeout=1)
            except Exception:
                pass  

    def _failure_detector_loop(self) -> None:
        """
        A loop that detects dead nodes and removes them from the routing table.
        """
        while self.running:
            now = time.time()
            dead = []
            with self.lock:
                for node_id, ts in self.last_seen.items():
                    if node_id == self.self_node_id:
                        continue
                    if now - ts > FAILURE_HARD_DEAD and self.status_map.get(node_id) != "dead":
                        self.status_map[node_id] = "dead"
                        dead.append(node_id)
            for node_id in dead:
                print(f"[Gossip] Node {node_id} marked as DEAD")
                host, port = get_host_port(node_id)
                self.routing_table.remove_node(host, port)
                # Clean up dead nodes from maintained variables
                with self.lock:
                    try:
                        del self.heartbeat_map[node_id]
                        del self.last_seen[node_id]
                        del self.status_map[node_id]
                    except KeyError:
                        pass
            time.sleep(FAILURE_DETECT_INTERVAL)

    def receive_gossip(self, data: dict) -> None:
        """
        Receives a gossip message from another node.
        """
        if not isinstance(data, dict) or \
            any(field not in data for field in ["sender", "heartbeat_map", "routing_table"]) or \
            not isinstance(data["heartbeat_map"], dict) or \
            not isinstance(data["routing_table"], dict) or \
            not isinstance(data["sender"], str):
            print("[Gossip] Error: Invalid data format")
            return

        with self.lock:
            incoming_hb = data.get("heartbeat_map", {})
            for node_id, hb in incoming_hb.items():
                local_hb = self.heartbeat_map.get(node_id, -1)
                if hb > local_hb:
                    self.heartbeat_map[node_id] = hb
                    self.last_seen[node_id] = time.time()
                    self.status_map[node_id] = "alive"

            remote_rt = data.get("routing_table", {})
            remote_version = remote_rt.get("version", 0)
            remote_uid = remote_rt.get("uid", "")
            local_version = self.routing_table.version
            local_uid = self.routing_table.uid

            if remote_version > local_version:
                self.routing_table.replace_with(remote_rt)
            elif remote_version == local_version and remote_uid != local_uid:
                print("[Gossip] Version match but UID conflict: merging routing tables")
                self.routing_table.merge_with(remote_rt)

    def force_gossip_once(self) -> None:
        """
        Forces a gossip message to be sent to a random node.
        """
        peers = [n for n in self.routing_table.node_map.keys() if n != self.self_node_id]
        if peers:
            targets = random.sample(peers, min(GOSSIP_FANOUT, len(peers)))
            self._send_gossip(targets)
