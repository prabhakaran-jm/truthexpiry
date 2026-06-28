import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LifecycleMcpServerSettings:
    host: str = "127.0.0.1"
    port: int = 8000

    @classmethod
    def from_env(cls) -> "LifecycleMcpServerSettings":
        host = os.environ.get("TRUTH_EXPIRY_LIFECYCLE_MCP_HOST", "127.0.0.1").strip()
        port_raw = os.environ.get("TRUTH_EXPIRY_LIFECYCLE_MCP_PORT", "8000").strip()
        return cls(host=host, port=int(port_raw))
