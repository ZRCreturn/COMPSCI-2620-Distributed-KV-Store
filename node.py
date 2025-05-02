from fastapi import FastAPI, Request, HTTPException, Header
from pydantic import BaseModel
import uvicorn
import sys
import requests
import random
import logging

from routing_table import RoutingTable
from gossip import GossipManager
from data_migrator import DataMigrator
from config import BOOTSTRAP_NODE

app = FastAPI()

class PutRequest(BaseModel):
    key: str
    value: str

class JoinRequest(BaseModel):
    host: str
    port: int

class Node:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.node_id = f"{host}:{port}"
        self.storage = {}

        self.routing_table = RoutingTable(self_host=self.host, self_port=self.port)
        self.gossip = GossipManager(self_node_id=self.node_id, routing_table=self.routing_table)
        self.migrator = DataMigrator(self)

        self.gossip.start()
        self.migrator.start()

    def is_responsible(self, key):
        node = self.routing_table.get_responsible_node(key)
        return node.node_id == self.node_id

    def put(self, key, value):
        if self.is_responsible(key):
            self.storage[key] = value
            return {"status": "ok", "message": f"Key {key} stored on {self.node_id}"}
        else:
            raise HTTPException(status_code=403, detail="This node is not responsible for this key")

    def get(self, key):
        if self.is_responsible(key):
            if key in self.storage:
                return {"key": key, "value": self.storage[key]}
            else:
                raise HTTPException(status_code=404, detail="Key not found")
        else:
            raise HTTPException(status_code=403, detail="This node is not responsible for this key")

    def check_routing_version(self, client_version):
        if client_version is None:
            return self.routing_table.serialize()
        try:
            client_version = int(client_version)
        except ValueError:
            return self.routing_table.serialize()
        if client_version < self.routing_table.version:
            return self.routing_table.serialize()
        return None

    def bootstrap_join(self, bootstrap_host, bootstrap_port):
        if str(self.host).strip() == str(bootstrap_host) and int(self.port) == int(bootstrap_port):
            return 
        bootstrap_url = f"http://{bootstrap_host}:{bootstrap_port}/routing_table"
        try:
            resp = requests.get(bootstrap_url, timeout=2)
            data = resp.json()
            all_nodes = data.get("nodes", [])
            candidates = [
                n for n in all_nodes if n["node_id"] != self.node_id
            ]
            if not candidates:
                print("[Join] No candidates found in routing table (only self?)")
                return
            target = random.choice(candidates)
            join_url = f"http://{target['host']}:{target['port']}/join"
            join_data = {"host": self.host, "port": self.port}
            join_resp = requests.post(join_url, json=join_data, timeout=2)
            print(f"[Join] Joined via {target['node_id']}: {join_resp.json()}")
        except Exception as e:
            print(f"[Join] Failed to join via bootstrap {bootstrap_url}: {e}")

node = None

class ExcludeGossipFilter(logging.Filter):
    def filter(self, record):
        return '/gossip' not in record.getMessage()   
access_log = logging.getLogger("uvicorn.access")
access_log.addFilter(ExcludeGossipFilter())

@app.put("/kv")
async def put_kv(req: PutRequest, routing_version: str = Header(None)):
    routing_update = node.check_routing_version(routing_version)
    result = node.put(req.key, req.value)
    if routing_update:
        result["routing_table"] = routing_update
    return result

@app.get("/kv")
async def get_kv(key: str, routing_version: str = Header(None)):
    routing_update = node.check_routing_version(routing_version)
    result = node.get(key)
    if routing_update:
        result["routing_table"] = routing_update
    return result

@app.post("/join")
async def join_network(req: JoinRequest):
    node.routing_table.add_node(req.host, req.port)
    node.gossip.force_gossip_once()
    return {"status": "ok", "message": f"{req.host}:{req.port} added to routing table."}

@app.post("/gossip")
async def receive_gossip(request: Request):
    data = await request.json()
    node.gossip.receive_gossip(data)
    return {"status": "ok"}

@app.get("/routing_table")
async def get_routing_table():
    return node.routing_table.serialize()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python node.py <host> <port>")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    node = Node(host=host, port=port)
    default_bootstrap_host, default_bootstrap_port = BOOTSTRAP_NODE.split(":")
    node.bootstrap_join(default_bootstrap_host, default_bootstrap_port)

    uvicorn.run(app, host=host, port=port)
