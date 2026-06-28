# Milestone 1 — Lifecycle MCP

Milestone 1 adds a **local, read-only Streamable HTTP MCP server** that returns synthetic Jira-like lifecycle evidence. The Slack app can use **real lifecycle MCP** while RTS and claim extraction remain on fake adapters.

**Not production-ready:** localhost-only, unauthenticated, synthetic data only.

## Architecture

```text
TruthExpiryPipeline
    → LifecycleEvidencePort
    → LifecycleMcpAdapter (or FakeLifecycleEvidenceAdapter)
    → Streamable HTTP MCP (optional)
    → lifecycle_mcp.server
    → LifecycleRecordRepository
    → lifecycle_mcp/data/lifecycle_records.json
    → truthexpiry/services/labeler.py  (assigns CURRENT / SUPERSEDED / CONFLICTING / UNVERIFIED)
```

- **MCP server** returns evidence records only. It never assigns validity labels.
- **Domain labeler** applies deterministic rules using `ClockPort.today()`.
- **Canonical dataset** is shared by the MCP server and `FakeLifecycleEvidenceAdapter` via `LifecycleRecordRepository` (no MCP imports in the repository).

## Package layout

```text
lifecycle_mcp/
  server.py              # python -m lifecycle_mcp.server
  server_settings.py     # TRUTH_EXPIRY_LIFECYCLE_MCP_HOST / PORT
  contracts.py           # GetLifecycleEvidenceOutput DTOs
  repository.py          # transport-free JSON loader
  smoke.py               # client smoke CLI
  data/lifecycle_records.json

adapters/lifecycle_mcp/
  client.py              # streamable_http_client + ClientSession
  mapper.py              # structuredContent → LifecycleRecord
  sync_bridge.py         # run_mcp_call(factory)
  adapter.py             # LifecycleMcpAdapter
```

## MCP tool contract

**Tool:** `get_lifecycle_evidence` (only tool)

**Flat arguments:**

```json
{
  "entity": "report_export",
  "attribute": "availability",
  "scope": { "plan": "starter", "region": "global" }
}
```

**Structured output** (`CallToolResult.structuredContent`):

```json
{
  "schema_version": "1",
  "source": "truth-expiry-lifecycle-mcp",
  "records": [
    {
      "record_id": "PROD-482",
      "entity": "report_export",
      "attribute": "availability",
      "scope": { "plan": "starter", "region": "global" },
      "value": "disabled",
      "state": "SHIPPED",
      "effective_date": "2026-05-12",
      "supersedes_record_id": "PROD-481"
    }
  ]
}
```

The client adapter reads **`structuredContent` only** — never plain-text `content`.

## Composition modes

| Configuration | RTS | Claim extraction | Lifecycle evidence |
|---------------|-----|------------------|------------------|
| `TRUTH_EXPIRY_USE_FAKES=1` | Fake | Fake | Fake (same JSON repo) |
| Fakes unset + `TRUTH_EXPIRY_LIFECYCLE_MCP_URL` set | Fake | Fake | **Real MCP** |
| Fakes unset + URL missing | — | — | **Composition error** at startup |

## Fail-closed behavior

| Outcome | Pipeline result |
|---------|-----------------|
| Successful MCP response with `records: []` | Labeler: no matching evidence (`UNVERIFIED` with “no evidence” explanation) |
| MCP transport failure or invalid structured response | `UNVERIFIED` — “Authoritative lifecycle evidence is currently unavailable.” |

MCP failures are **not** converted to empty record lists.

## Local commands

### Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

### Start lifecycle MCP server

```powershell
$env:TRUTH_EXPIRY_LIFECYCLE_MCP_HOST = "127.0.0.1"
$env:TRUTH_EXPIRY_LIFECYCLE_MCP_PORT = "8000"
python -m lifecycle_mcp.server
```

Endpoint: `http://127.0.0.1:8000/mcp`

### Client smoke (record IDs only)

```powershell
python -m lifecycle_mcp.smoke --url http://127.0.0.1:8000/mcp
```

### Slack app — all fakes

```powershell
$env:TRUTH_EXPIRY_USE_FAKES = "1"
python app.py
```

### Slack app — real lifecycle MCP (RTS + LLM still fake)

```powershell
# Terminal 1: start server (see above)

# Terminal 2 — do NOT set TRUTH_EXPIRY_USE_FAKES
$env:TRUTH_EXPIRY_LIFECYCLE_MCP_URL = "http://127.0.0.1:8000/mcp"
python app.py
```

## Verification

```powershell
ruff check .
ruff format --check .
mypy truthexpiry adapters lifecycle_mcp listeners agent
pytest -q
pytest -q tests/integration/test_lifecycle_mcp_transport.py
pytest -q tests/contract/test_lifecycle_mcp_tool_contract.py
pip-audit -r requirements.txt
git diff --check
```

Secret scan:

```powershell
git grep -E "xox[baprs]-|sk-[A-Za-z0-9]{10,}|ANTHROPIC_API_KEY=\S+|OPENAI_API_KEY=\S+" -- ":!*.sample" ":!.env.sample"
```

## M1 exclusions (out of scope)

- Slack RTS (`assistant.search.*`)
- Slack MCP / OAuth
- Private Slack search
- Live LLM calls
- Database or persistence layer
- Cloud deployment
- Validity decisions inside the MCP server
- `evaluation_date` tool parameter
- Cross-thread / nested-event-loop MCP sync bridge

## Synthetic dataset scenarios

| Record ID | Scenario |
|-----------|----------|
| `PROD-481` / `PROD-482` | Report export enabled → disabled (`PROD-482` current shipped record) |
| `PROD-501` | Matching current authoritative state (analytics export) |
| `PROD-510` / `PROD-511` | Explicit supersession (rate limit) |
| `PROD-520-A` / `PROD-520-B` | Conflicting active records (billing refund) |
| `PROD-530` | Future-effective evidence |
| `PROD-540` | Planned (not yet authoritative) |
| `PROD-541` | Cancelled evidence |
| *(no row)* | No-match for unrelated scope keys |

All IDs and values are invented. No real Slack workspace data appears in the dataset.
