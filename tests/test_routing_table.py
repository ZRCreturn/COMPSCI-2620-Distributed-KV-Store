import unittest
from routing_table import RoutingTable
from config import VIRTUAL_NODE_REPLICAS

class TestRoutingTable(unittest.TestCase):
    def setUp(self):
        """Set up a fresh routing table before each test"""
        self.rt = RoutingTable("127.0.0.1", 8000)

    def test_initialization(self):
        """Test that the routing table initializes correctly"""
        self.assertEqual(self.rt.version, 2)
        self.assertIsNotNone(self.rt.uid)
        self.assertEqual(len(self.rt.node_map), 1)  # Should have self node
        self.assertEqual(len(self.rt.virtual_nodes), VIRTUAL_NODE_REPLICAS)

    def test_add_node(self):
        """Test adding a new node"""
        initial_version = self.rt.version
        initial_uid = self.rt.uid
        
        self.rt.add_node("127.0.0.1", 8001)
        
        # Check version and uid changed
        self.assertGreater(self.rt.version, initial_version)
        self.assertNotEqual(self.rt.uid, initial_uid)
        
        # Check node was added
        self.assertEqual(len(self.rt.node_map), 2)
        self.assertEqual(len(self.rt.virtual_nodes), 2 * VIRTUAL_NODE_REPLICAS)

        # Test adding an added node again
        self.rt.add_node("127.0.0.1", 8001)
        self.assertEqual(len(self.rt.node_map), 2)
        self.assertEqual(len(self.rt.virtual_nodes), 2 * VIRTUAL_NODE_REPLICAS)

    def test_remove_node(self):
        """Test removing a node"""
        self.rt.add_node("127.0.0.1", 8001)
        initial_version = self.rt.version
        initial_uid = self.rt.uid
        
        self.rt.remove_node("127.0.0.1", 8001)
        
        # Check version and uid changed
        self.assertGreater(self.rt.version, initial_version)
        self.assertNotEqual(self.rt.uid, initial_uid)
        
        # Check node was removed
        self.assertEqual(len(self.rt.node_map), 1)
        self.assertEqual(len(self.rt.virtual_nodes), VIRTUAL_NODE_REPLICAS)

        # Test removing a non-existent node
        self.rt.remove_node("127.0.0.1", 8001)
        self.assertEqual(len(self.rt.node_map), 1)
        self.assertEqual(len(self.rt.virtual_nodes), VIRTUAL_NODE_REPLICAS)

    def test_get_responsible_node(self):
        """Test finding responsible node for a key"""
        self.rt.add_node("127.0.0.1", 8001)
        
        # Test with a known key
        key = "test_key"
        responsible_node = self.rt.get_responsible_node(key)
        
        # Check that we got a valid node
        self.assertIsNotNone(responsible_node)
        self.assertIn(responsible_node.node_id, self.rt.node_map)

    def test_serialize(self):
        """Test serialization of routing table"""
        serialized = self.rt.serialize()
        
        # Check structure
        self.assertIn("version", serialized)
        self.assertIn("uid", serialized)
        self.assertIn("nodes", serialized)
        
        # Check content
        self.assertEqual(serialized["version"], self.rt.version)
        self.assertEqual(serialized["uid"], self.rt.uid)
        self.assertEqual(len(serialized["nodes"]), len(self.rt.node_map))

    def test_replace_with(self):
        """Test replacing routing table with remote one"""
        # Create a remote routing table
        remote_rt = {
            "version": 5,
            "uid": "test-uid",
            "nodes": [
                {"host": "127.0.0.1", "port": 8002},
                {"host": "127.0.0.1", "port": 8003}
            ]
        }
        
        self.rt.replace_with(remote_rt)
        
        # Check that the routing table was replaced
        self.assertEqual(self.rt.version, 5)
        self.assertEqual(self.rt.uid, "test-uid")
        self.assertEqual(len(self.rt.node_map), 2)

    def test_merge_with(self):
        """Test merging with a remote routing table"""
        # Add some nodes to current routing table
        self.rt.add_node("127.0.0.1", 8001)
        
        # Create a remote routing table with some overlapping and some new nodes
        remote_rt = {
            "version": 5,
            "uid": "test-uid",
            "nodes": [
                {"host": "127.0.0.1", "port": 8001},  # Overlapping
                {"host": "127.0.0.1", "port": 8002}   # New
            ]
        }
        
        initial_version = self.rt.version
        self.rt.merge_with(remote_rt)
        
        # Check that only new nodes were added
        self.assertEqual(len(self.rt.node_map), 3)  # Original + 8001 + 8002
        self.assertGreater(self.rt.version, initial_version)

    def test_hash_ring_consistency(self):
        """Test that the hash ring maintains consistent ordering"""
        self.rt.add_node("127.0.0.1", 8001)
        self.rt.add_node("127.0.0.1", 8002)
        
        # Check that virtual nodes are sorted by hash
        hashes = [v.hash for v in self.rt.virtual_nodes]
        self.assertEqual(hashes, sorted(hashes))

    def test_debug_print(self):
        """Test that the debug print method works"""
        self.rt.debug_print()
