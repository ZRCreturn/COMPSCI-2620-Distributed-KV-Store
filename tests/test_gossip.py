from routing_table import RoutingTable
from gossip import GossipManager

class DummyRoutingTable(RoutingTable):
    def __init__(self):
        super().__init__()
        # Simplify version/uid control


def test_gossip_replaces_older_routing_table(monkeypatch):
    rt_local = RoutingTable()
    rt_remote = RoutingTable()
    rt_local.add_node("127.0.0.1", 8000)
    rt_remote.add_node("127.0.0.1", 8000)
    # Simulate remote with higher version
    rt_remote.version = rt_local.version + 1

    gm = GossipManager(self_node_id="127.0.0.1:8000", routing_table=rt_local)
    # Monkey-patch HTTP send to no-op
    monkeypatch.setattr(gm, '_send_raw', lambda *args, **kwargs: None)

    gm._process_remote({
        "nodes": rt_remote.to_dict()["nodes"],
        "version": rt_remote.version,
        "uid": rt_remote.uid
    })
    assert rt_local.version == rt_remote.version


def test_gossip_merge_on_uid_conflict(monkeypatch, capsys):
    rt_local = RoutingTable()
    rt_remote = RoutingTable()
    # Same version but different uid
    rt_remote.version = rt_local.version
    rt_remote.uid = "different"
    gm = GossipManager(self_node_id="127.0.0.1:8000", routing_table=rt_local)
    gm._process_remote({
        "nodes": rt_remote.to_dict()["nodes"],
        "version": rt_remote.version,
        "uid": rt_remote.uid
    })
    captured = capsys.readouterr()
    assert "merging routing tables" in captured.out
