import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class LifecycleMcpUsageError(RuntimeError):
    """Raised when run_mcp_call is used inside a running event loop."""


def run_mcp_call(factory: Callable[[], Awaitable[T]]) -> T:
    """Run an MCP client coroutine from synchronous code.

    The factory must create a fresh coroutine on each call.
    Do not pass a pre-created coroutine across threads or loops.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(factory())
    raise LifecycleMcpUsageError(
        "Lifecycle MCP cannot be called from a running event loop in Milestone 1."
    )
