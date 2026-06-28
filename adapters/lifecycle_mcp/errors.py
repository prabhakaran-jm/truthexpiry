class LifecycleMcpResponseError(Exception):
    """Invalid or unsupported MCP tool response."""


class LifecycleMcpTransportError(Exception):
    """MCP transport or session failure."""
