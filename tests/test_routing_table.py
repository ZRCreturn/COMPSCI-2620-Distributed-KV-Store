import pytest
from routing_table import RoutingTable, hash_str

@pytest.mark.parametrize("key", ["foo", "bar", "baz"])
def test_hash_str_is_deterministic(key):
    h1 = hash_str(key)
    h2 = hash_str(key)
    assert isinstance(h1, int)
    assert h1 == h2


def test_add_and_remove_node_updates_version_and_map():
    rt = RoutingTable()
    initial_version = rt.version
    # Add a node
    rt.add_node("127.0.0.1", 8000)
    assert "127.0.0.1:8000" in rt.node_map
    assert rt.version == initial_version + 1
    # Remove the node
    rt.remove_node("127.0.0.1", 8000)
    assert "127.0.0.1:8000" not in rt.node_map
    assert rt.version == initial_version + 2


def test_get_responsible_node_wraps_around():
    rt = RoutingTable()
    # Create two nodes far apart on the ring
    rt.add_node("127.0.0.1", 8000)
    rt.add_node("127.0.0.1", 8001)
    # Choose an extreme key to force wrap-around behavior
    key = "zzzzzzzz"
    node = rt.get_responsible_node(key)
    assert node in rt.node_map
