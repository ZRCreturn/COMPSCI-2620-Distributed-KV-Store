import threading
import time
import requests

class DataMigrator:
    def __init__(self, node):
        self.node = node
        self.last_version = node.routing_table.version
        self.lock = threading.Lock()
        self.running = False

    def start(self):
        """启动后台线程"""
        self.running = True
        threading.Thread(target=self._migration_loop, daemon=True).start()

    def _migration_loop(self):
        while self.running:
            time.sleep(5)  # 每5秒检测一次（可配置）
            self._check_and_migrate()

    def _check_and_migrate(self):
        with self.lock:
            current_version = self.node.routing_table.version
            if current_version == self.last_version:
                return  # 版本没变，不做任何事

            print(f"[Migrator] Detected routing_table version change: {self.last_version} -> {current_version}")
            self.last_version = current_version
            self._migrate_data()

    def _migrate_data(self):
        keys_to_move = []
        for key in list(self.node.storage.keys()):
            responsible_node = self.node.routing_table.get_responsible_node(key)
            if responsible_node.node_id != self.node.node_id:
                keys_to_move.append((key, self.node.storage[key], responsible_node))

        if not keys_to_move:
            print("[Migrator] No data to migrate.")
            return

        print(f"[Migrator] {len(keys_to_move)} keys need to be moved.")

        for key, value, target_node in keys_to_move:
            try:
                url = f"http://{target_node.host}:{target_node.port}/kv"
                headers = {"Routing-Version": str(self.node.routing_table.version)}
                resp = requests.put(url, json={"key": key, "value": value}, headers=headers)
                if resp.status_code == 200:
                    del self.node.storage[key]
                    print(f"[Migrator] Migrated key '{key}' to {target_node.node_id}")
                else:
                    print(f"[Migrator] Failed to migrate key '{key}' to {target_node.node_id}: {resp.text}")
            except Exception as e:
                print(f"[Migrator] Error migrating key '{key}': {e}")
