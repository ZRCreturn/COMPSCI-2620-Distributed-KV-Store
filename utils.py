import hashlib

def hash_str(s):
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest(), 16) % (2 ** 64)

def get_host_port(node_id: str) -> tuple[str, int]:
    try:
        host, port = node_id.split(":")
        return host, int(port)
    except Exception as e:
        raise Exception(f"Invalid node ID: {node_id}") from e
