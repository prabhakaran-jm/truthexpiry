import asyncio

import pytest

from adapters.lifecycle_mcp.sync_bridge import LifecycleMcpUsageError, run_mcp_call


async def _returns_value() -> str:
    return "ok"


def test_sync_bridge_runs_coroutine_factory_without_active_loop():
    assert run_mcp_call(_returns_value) == "ok"


def test_sync_bridge_rejects_active_event_loop():
    async def _run_inside_loop() -> None:
        with pytest.raises(LifecycleMcpUsageError, match="running event loop"):
            run_mcp_call(_returns_value)

    asyncio.run(_run_inside_loop())
