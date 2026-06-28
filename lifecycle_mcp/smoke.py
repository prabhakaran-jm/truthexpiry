"""Client smoke CLI for the lifecycle MCP server."""

from __future__ import annotations

import argparse
import asyncio
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from adapters.lifecycle_mcp.mapper import map_structured_content
from lifecycle_mcp.contracts import TOOL_NAME
from truthexpiry.services.claim_key import build_claim_key


async def _run_smoke(url: str) -> list[str]:
    claim_key = build_claim_key(
        "report_export",
        "availability",
        {"plan": "starter", "region": "global"},
    )
    async with streamable_http_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            await session.list_tools()
            result = await session.call_tool(
                TOOL_NAME,
                {
                    "entity": claim_key.entity,
                    "attribute": claim_key.attribute,
                    "scope": dict(claim_key.scope.fields),
                },
            )
            records = map_structured_content(result, claim_key)
            return [record.record_id for record in records]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lifecycle MCP client smoke test")
    parser.add_argument(
        "--url",
        required=True,
        help="Streamable HTTP MCP endpoint, e.g. http://127.0.0.1:8000/mcp",
    )
    args = parser.parse_args(argv)
    record_ids = asyncio.run(_run_smoke(args.url))
    for record_id in record_ids:
        print(record_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
