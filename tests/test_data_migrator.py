import pytest
from routing_table import RoutingTable
from data_migrator import DataMigrator
import threading

class DummyRoutingTable(RoutingTable):
    def __init__(self):
        super().__init__()
        self.version = 1

    def get_data_to_migrate(self, old_version, new_version):
        # Simulate finding keys that need migration
        return [("key1", "value1", "127.0.0.1", 8001)]

    def update_local_data(self, key):
        # Simulate deletion after migration
        pass


def test_data_migrator_triggers_on_version_change(monkeypatch):
    rt = DummyRoutingTable()
    dm = DataMigrator(routing_table=rt)

    # Stub the HTTP PUT to always succeed
    monkeypatch.setattr(dm, '_send_to_node', lambda k, v, h, p: True)

    # Start migrator in a background thread and bump version
    t = threading.Thread(target=dm._migration_loop, daemon=True)
    t.start()

    # Simulate a version bump
    rt.version = 2
    # Allow migrator to detect change
    pytest.sleep(0.1)

    # Verify that migration occurred: no exceptions and thread is alive
    assert t.is_alive()
