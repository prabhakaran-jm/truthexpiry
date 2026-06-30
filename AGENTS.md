# TruthExpiry — agent instructions

Canonical architecture and development rules for humans and coding agents working in this repository.

## Purpose

TruthExpiry prevents Slack agents from repeating stale information. A user asks a question in Slack. The app retrieves candidate claims from **public channels**, obtains authoritative lifecycle evidence, and uses **deterministic rules** to label each claim:

- `CURRENT`
- `SUPERSEDED`
- `CONFLICTING`
- `UNVERIFIED`

**The LLM extracts claims only. It never assigns validity.**

## Milestones

| Milestone | Scope |
|-----------|--------|
| **M0** | Scaffold merge, domain package, ports, fake adapters, listener boundary, offline tests, tooling. **No live RTS, MCP, or LLM.** |
| **M1** | Real local Streamable HTTP lifecycle MCP (`TRUTH_EXPIRY_LIFECYCLE_MCP_URL`); synthetic Jira-like records in `lifecycle_mcp/data/lifecycle_records.json`. RTS and LLM remain fake. |
| **M2** | Live public-channel RTS via `assistant.search.context` (one call per request); fake extraction; real lifecycle MCP when configured. See [docs/MILESTONE_2.md](docs/MILESTONE_2.md). |
| **M3** | OpenAI-backed live claim extraction via `TRUTH_EXPIRY_CLAIM_EXTRACTOR=live`; domain claim-schema catalog; evidence-ID grounding. See [docs/MILESTONE_3.md](docs/MILESTONE_3.md). |
| **M4** | Operational hardening: split config validation, health/readiness probes, bearer MCP auth, graceful shutdown, structured logging, metrics, containers. See [docs/MILESTONE_4.md](docs/MILESTONE_4.md). |

Do not implement later-milestone integrations unless explicitly requested. See [docs/MILESTONE_1.md](docs/MILESTONE_1.md), [docs/MILESTONE_2.md](docs/MILESTONE_2.md), [docs/MILESTONE_3.md](docs/MILESTONE_3.md), and [docs/MILESTONE_4.md](docs/MILESTONE_4.md).

## MVP constraints (public channels)

- Socket Mode with bot token and event `action_token` (M2 for live RTS).
- **Public Slack channels only** for workspace search evidence.
- No private-channel, DM, or MPDM search in the MVP.
- No user-token OAuth until the public-channel flow works.
- `manifest.json` has `is_mcp_enabled: false` and bot scope `search:read.public` only (no user OAuth scopes).

## Package layout

```
truthexpiry/          # Pure domain — no slack_sdk, no network I/O, no mcp imports
  config/             # SlackWorkerSettings, ConfigError, SecretValue (M4)
  ops/                # health, logging, metrics, shutdown, readiness (M4)
  models/             # ClaimKey, LifecycleRecord, ValidationResult, etc.
  ports/              # RtsPort, LifecycleEvidencePort, ClaimExtractionPort, ClockPort
  services/           # pipeline, labeler, claim_key, search_plan, rts_sanitizer

adapters/
  composition.py      # build_pipeline(); M2 startup composition with app.client
  fakes/              # FakeRtsPort, FakeLifecycleEvidenceAdapter, FakeClaimExtractionPort
  lifecycle_mcp/      # LifecycleMcpAdapter, client, mapper, sync_bridge
  slack_rts/          # SlackRtsAdapter via assistant.search.context api_call
  llm/                # PydanticAiClaimExtractionAdapter (M3 live extraction)

lifecycle_mcp/        # Read-only Streamable HTTP MCP server + canonical JSON dataset
  server.py           # python -m lifecycle_mcp.server
  repository.py       # transport-free; shared by server and fake adapter
  data/lifecycle_records.json

listeners/            # Thin Bolt boundary — delegate to TruthExpiryPipeline only
agent/                # Deferred live LLM extraction (NotImplementedError in M0)

app.py                # Socket Mode entrypoint; --check for structural config validation (M4)
```

**M4 operations:** Worker exposes `/healthz` and `/readyz` on `TRUTH_EXPIRY_HEALTH_PORT` (default `8080`). When `TRUTH_EXPIRY_METRICS_ENABLED=1`, Prometheus text metrics are served on `TRUTH_EXPIRY_METRICS_PORT` (default `9090`) at `/metrics`. Lifecycle MCP health binds to `TRUTH_EXPIRY_LIFECYCLE_MCP_HEALTH_PORT` (default `8001`). See [docs/runbooks/deployment.md](docs/runbooks/deployment.md).

**Listeners must not contain business logic.** They parse Slack events, build `TruthExpiryRequest`, call the injected `TruthExpiryPipeline`, and render the response.

## User-triggered entry points

- `message.im` — direct messages and assistant panel threads
- `app_mention` — @mentions in public channels

Do not invent custom Slack event types. Do not handle top-level channel messages without a mention unless manifest and product scope explicitly require it.

## Claim identity

Claim identity is **not** a permalink, message timestamp, or ticket ID.

**Normalized claim key:** `entity + attribute + normalized scope`

Example canonical form:

```text
report_export|availability|plan=starter|region=global
```

**Evidence references only:** Slack permalink, `(channel_id, message_ts)`, external ticket IDs (e.g. `PROD-482`).

## Deterministic status rules

Four statuses only. Implement and test in `truthexpiry/services/labeler.py`.

### CURRENT

- Authoritative lifecycle record matches entity, attribute, and scope.
- State is `SHIPPED` or `EFFECTIVE`.
- Effective date has arrived.
- Value matches the claim.
- No unresolved authoritative contradiction.

A Slack message alone cannot make a claim `CURRENT` unless explicit configured authority and owner-confirmation policy allow it.

### SUPERSEDED

- Later `SHIPPED` or `EFFECTIVE` record matches same entity, attribute, scope.
- Lifecycle value conflicts with the claim.
- New record explicitly supersedes the old **or** has a later effective date.

**Message timestamps alone must never cause supersession.**

### CONFLICTING

- Two active authoritative records match same entity, attribute, scope.
- Values disagree.
- No configured precedence resolves the disagreement.

Do not hide either source.

### UNVERIFIED

- No matching authoritative lifecycle evidence.
- Evidence only proposed/planned/cancelled/rejected/draft/not yet effective.
- Required scope fields missing.
- Lifecycle response cannot be validated.
- **M1:** Authoritative lifecycle MCP is unavailable (transport or structured response failure). The pipeline fail-closes with an explicit unavailable explanation — it does not treat MCP errors as an empty evidence list.

## No retention of Slack-derived content

**Must not persist anywhere** (memory across requests, disk, logs, traces, caches, fixtures, error reports):

- RTS results (raw or sanitized message text)
- Retrieved message text or file content
- LLM history containing retrieved Slack content
- Generated summaries containing copied Slack content

**Processing model:**

- Request-scoped objects only during a single handler invocation.
- After the Slack response is rendered, discard all Slack-derived content.
- Follow-up turns re-fetch when live integration exists (M2) — never load retained message text from a store.

**Allowed persistent metadata only** (future milestones):

- Slack permalink, channel ID, message timestamp (evidence refs, not claim identity)
- Evidence type, user-confirmed status, normalized entity key, external lifecycle record ID
- Ticket references as evidence links only

The scaffold `thread_context/` store is removed. Do not reintroduce conversation persistence.

## Ports and adapters

| Port | M0 | M1 | M2 | M3 |
|------|----|----|-----|-----|
| `RtsPort` | `FakeRtsPort` | `FakeRtsPort` | `SlackRtsAdapter` when fakes unset and `app.client` injected | same as M2 |
| `LifecycleEvidencePort` | `FakeLifecycleEvidenceAdapter` | `LifecycleMcpAdapter` when `TRUTH_EXPIRY_LIFECYCLE_MCP_URL` is set | same as M1 | same as M2 |
| `ClaimExtractionPort` | `FakeClaimExtractionPort` | `FakeClaimExtractionPort` | `FakeClaimExtractionPort` (default) | `PydanticAiClaimExtractionAdapter` when `TRUTH_EXPIRY_CLAIM_EXTRACTOR=live` |
| `ClockPort` | `SystemClock` | `SystemClock` | `SystemClock` | `SystemClock` |

Composition: `adapters/composition.py`.

```text
TRUTH_EXPIRY_USE_FAKES=1
    → all adapters fake (RTS, lifecycle, LLM)

TRUTH_EXPIRY_USE_FAKES unset + app.client + TRUTH_EXPIRY_LIFECYCLE_MCP_URL
    → SlackRtsAdapter + LifecycleMcpAdapter + claim extractor from selector

TRUTH_EXPIRY_CLAIM_EXTRACTOR unset
    → FakeClaimExtractionPort (default)

TRUTH_EXPIRY_CLAIM_EXTRACTOR=live + OPENAI_API_KEY
    → PydanticAiClaimExtractionAdapter

TRUTH_EXPIRY_USE_FAKES unset + missing client or MCP URL
    → LiveAdaptersUnavailableError at composition time
```

Both fake and real lifecycle adapters read the same canonical JSON via `LifecycleRecordRepository`. The MCP server does **not** assign validity labels.

**Do not use `PYTEST_CURRENT_TEST` in production code.** Inject fakes via explicit DI or `build_pipeline()` in tests.

## Lifecycle MCP (M1)

- **Server:** `python -m lifecycle_mcp.server` — Streamable HTTP at `/mcp`, `stateless_http=True`, binds `127.0.0.1` by default.
- **Client:** `LifecycleMcpAdapter` reads `TRUTH_EXPIRY_LIFECYCLE_MCP_URL` only (not host/port).
- **Tool:** `get_lifecycle_evidence(entity, attribute, scope)` — flat args, no `evaluation_date`, no request wrapper.
- **Contract:** read `CallToolResult.structuredContent` only; never parse plain-text `content`.
- **Sync bridge:** `run_mcp_call(factory)` from sync Bolt handlers; raises `LifecycleMcpUsageError` inside a running event loop.
- **Smoke:** `python -m lifecycle_mcp.smoke --url http://127.0.0.1:8000/mcp`
- **Synthetic data only** — not production-ready; no real Slack data in the dataset.

**M1 exclusions:** Slack RTS, Slack MCP, OAuth, private search, live LLM, database, cloud deployment, validity inside MCP server.

## Slack MCP

**Disabled in M0.** Do not add `MCPServerStreamableHTTP` to the agent. RTS discovery stays application-controlled through `RtsPort`. Use direct Slack Web API for rendering.

## Slack RTS (M2)

- One `assistant.search.context` call per user invocation; **no** per-request `assistant.search.info`.
- Always send `disable_semantic_search=False`; Slack handles semantic vs keyword fallback.
- `slack-sdk==3.42.0` lacks a generated helper — use `client.api_call("assistant.search.context", ...)`.
- Public channels only (`channel_types=["public_channel"]`, `content_types=["messages"]`).
- Pass event RTS `action_token` from listener (`action_token` or `assistant_thread.action_token`); validate only in `SlackRtsAdapter`.
- RTS is available for internal apps and directory-published apps — not unlisted distributed apps.
- Treat returned content as ephemeral; ticket extraction happens in `rts_sanitizer.py`.

## Environment variables

| Variable | When | Purpose |
|----------|------|---------|
| `SLACK_BOT_TOKEN` | Slack runs | Bot token |
| `SLACK_APP_TOKEN` | Socket Mode | App-level token |
| `TRUTH_EXPIRY_USE_FAKES=1` | Local / tests | All adapters fake |
| `TRUTH_EXPIRY_LIFECYCLE_MCP_URL` | M1/M2 client | Streamable HTTP lifecycle MCP endpoint (e.g. `http://127.0.0.1:8000/mcp`) |
| `TRUTH_EXPIRY_LIFECYCLE_MCP_HOST` | M1 server | Server bind host (default `127.0.0.1`) |
| `TRUTH_EXPIRY_LIFECYCLE_MCP_PORT` | M1 server | Server bind port (default `8000`) |
| `TRUTH_EXPIRY_CLAIM_EXTRACTOR` | M3 client | `fake` (default) or `live` (requires `OPENAI_API_KEY`) |
| `TRUTH_EXPIRY_LOG_LEVEL` | Optional | Default `INFO`; never log message text |
| `TRUTH_EXPIRY_LOG_FORMAT` | M4 | `text` (default) or `json` structured logs |
| `TRUTH_EXPIRY_HEALTH_HOST` / `TRUTH_EXPIRY_HEALTH_PORT` | M4 worker | Health bind (default `0.0.0.0:8080`) |
| `TRUTH_EXPIRY_METRICS_ENABLED` / `TRUTH_EXPIRY_METRICS_PORT` | M4 worker | Prometheus text on `/metrics` (default off, port `9090`) |
| `TRUTH_EXPIRY_DEDUP_EVENT_IDS` | M4 worker | Optional in-memory Slack `event_id` dedup (default off) |
| `TRUTH_EXPIRY_LIFECYCLE_MCP_HEALTH_URL` | M4 worker | Override MCP `/readyz` URL for startup poll (default derived from MCP URL + health port) |
| `TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN` | M4 live MCP | Bearer token; required unless `TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_DISABLED=1` |
| `TRUTH_EXPIRY_LIFECYCLE_MCP_HEALTH_PORT` | M4 MCP server | Health sidecar port (default `8001`) |
| `OPENAI_API_KEY` | M3 live extraction | Required when `TRUTH_EXPIRY_CLAIM_EXTRACTOR=live` |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | Post-M0 scaffold | Not used by M3 live extractor (OpenAI only) |

Document secrets in `.env.sample`. Never commit `.env` or tokens.

## Commands

From repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"

ruff check .
ruff format --check .
mypy truthexpiry adapters lifecycle_mcp listeners agent
pytest -q
pytest -q tests/integration/test_lifecycle_mcp_transport.py
pip-audit -r requirements.txt
```

Use the editable install so `truthexpiry` imports resolve to the worktree instead of a stale site-packages copy.

Local Slack run (optional, not required for CI):

```powershell
$env:TRUTH_EXPIRY_USE_FAKES = "1"
python app.py
```

Lifecycle MCP server + smoke (M1):

```powershell
python -m lifecycle_mcp.server
python -m lifecycle_mcp.smoke --url http://127.0.0.1:8000/mcp
```

## What not to commit

- `.cursor/`, `.claude/`, `.slack/`, `.env`, `data/`
- `scaffold/` or duplicate template trees
- Slack message text in fixtures or snapshots
- API keys or tokens

Milestone 0 uses `app.py` (Socket Mode) only. OAuth HTTP distribution (`app_oauth.py`) is removed until M2.

## Related docs

- [`REVIEW.md`](REVIEW.md) — pre-merge review checklist
- [`README.md`](README.md) — user-facing overview
- [`docs/MILESTONE_1.md`](docs/MILESTONE_1.md) — M1 lifecycle MCP architecture and verification
- [`docs/MILESTONE_2.md`](docs/MILESTONE_2.md) — M2 live Slack RTS architecture and manual acceptance
- [`docs/MILESTONE_3.md`](docs/MILESTONE_3.md) — M3 live claim extraction architecture and verification
- [`docs/MILESTONE_4.md`](docs/MILESTONE_4.md) — M4 operational hardening, probes, containers
- [`docs/SCAFFOLD_INSPECTION.md`](docs/SCAFFOLD_INSPECTION.md) — upstream scaffold inventory
