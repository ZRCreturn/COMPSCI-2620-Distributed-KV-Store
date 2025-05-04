import pytest
from client import SmartClient
from routing_table import RoutingTable

@pytest.fixture
def client(monkeypatch):
    # Initialize a SmartClient with a dummy routing table
    rt = RoutingTable()
    client = SmartClient(bootstrap_node="127.0.0.1:8000", routing_table=rt)
    # Monkey-patch HTTP requests to nodes
    monkeypatch.setattr(client, '_send_request', lambda *args, **kwargs: {"value": "v", "version": 1})
    return client

def test_client_put_get_refresh(client):
    client.put("k", "v")
    assert client.get("k") == "v"
    client.routing_table.version -= 1  # force stale
    client.refresh()  # should fetch new routing table
    assert client.routing_table.version == client.routing_table.version
