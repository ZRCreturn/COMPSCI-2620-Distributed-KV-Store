import requests
import random
import sys
from config import BOOTSTRAP_NODE
from routing_table import RoutingTable
from utils import hash_str, get_host_port
class SmartClient:
    def __init__(self):
        self.routing_table = None
        self.version = -1
        self.bootstrap_host, self.bootstrap_port = get_host_port(BOOTSTRAP_NODE)
        self.bootstrap_join()

    def bootstrap_join(self):
        try:
            url = f"http://{self.bootstrap_host}:{self.bootstrap_port}/routing_table"
            resp = requests.get(url, timeout=2)
            remote_rt = resp.json()
            self.version = remote_rt.get("version", -1)
            if self.routing_table is None:
                self.routing_table = RoutingTable(self_host="client", self_port=0)

            self.routing_table.replace_with(remote_rt)
            print(f"[Info] Routing table loaded. Version: {self.version}")

        except Exception as e:
            print(f"[Error] Failed to load routing table from bootstrap: {e}")
            sys.exit(1)

    def put(self, key, value):
        responsible_node = self.routing_table.get_responsible_node(key)
        url = f"http://{responsible_node.host}:{responsible_node.port}/kv"
        headers = {"Routing-Version": str(self.version)}
        try:
            resp = requests.put(url, json={"key": key, "value": value}, headers=headers)
            result = resp.json()
            print(f"[PUT Success] {result}")
            self._check_routing_update(result)
        except Exception as e:
            print(f"[PUT Error] {e}")

    def get(self, key):
        responsible_node = self.routing_table.get_responsible_node(key)
        url = f"http://{responsible_node.host}:{responsible_node.port}/kv"
        headers = {"Routing-Version": str(self.version)}
        try:
            resp = requests.get(url, params={"key": key}, headers=headers)
            result = resp.json()
            print(f"[GET Success] {result}")
            self._check_routing_update(result)
        except Exception as e:
            print(f"[GET Error] {e}")

    def show_ring(self):
        nodes = self.routing_table.node_map.values()
        node_hashes = []
        for node in nodes:
            node_hash = hash_str(node.node_id)
            node_hashes.append((node_hash, node.node_id))

        node_hashes.sort()

        print("\n[ Hash Ring ]")
        for h, node_id in node_hashes:
            print(f"-> {node_id} (hash={h})")
        print(f"-> back to {node_hashes[0][1]}\n")

    def _check_routing_update(self, result):
        rt = result.get("routing_table")
        if rt:
            remote_version = rt.get("version", -1)
            if remote_version > self.version:
                self.routing_table.replace_with(rt)
                print(f"[Info] Routing table updated to version {self.version}.")

def main():
    client = SmartClient()

    while True:
        try:
            cmd = input("[SmartClient] > ").strip()
            if not cmd:
                continue
            parts = cmd.split()
            action = parts[0].lower()

            if action == "put" and len(parts) >= 3:
                key = parts[1]
                value = " ".join(parts[2:])
                client.put(key, value)
            elif action == "get" and len(parts) == 2:
                key = parts[1]
                client.get(key)
            elif action == "show_ring" or action == "s":
                client.show_ring()
            elif action == "refresh" or action == "r":
                client.bootstrap_join()
            elif action in ["exit", "quit"]:
                print("Bye!")
                break
            else:
                print("Commands: put <key> <value> | get <key> | show_ring | refresh | exit")
        except KeyboardInterrupt:
            print("\nBye!")
            break

if __name__ == "__main__":
    main()
