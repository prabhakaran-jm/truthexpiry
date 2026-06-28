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
| **M1** | Real local Streamable HTTP lifecycle MCP (`TRUTH_EXPIRY_LIFECYCLE_MCP_URL`); synthetic Jira-like records. |
| **M2** | Live RTS via `assistant.search.info` + `assistant.search.context`; public channels only; Socket Mode + bot token + `action_token`. |

Do not implement later-milestone integrations in M0 unless explicitly requested.

## MVP constraints (public channels)

- Socket Mode with bot token and event `action_token` (M2 for live RTS).
- **Public Slack channels only** for workspace search evidence.
- No private-channel, DM, or MPDM search in the MVP.
- No user-token OAuth until the public-channel flow works.
- `manifest.json` has `is_mcp_enabled: false` and bot scope `search:read.public` only (no user OAuth scopes).

## Package layout

```
truthexpiry/          # Pure domain — no slack_sdk, no network I/O
  models/             # ClaimKey, LifecycleRecord, ValidationResult, etc.
  ports/              # RtsPort, LifecycleEvidencePort, ClaimExtractionPort, ClockPort
  services/           # pipeline, labeler, claim_key, search_plan, rts_sanitizer

adapters/
  composition.py      # build_pipeline() / get_pipeline(); TRUTH_EXPIRY_USE_FAKES=1 in M0
  fakes/              # FakeRtsPort, FakeLifecycleEvidenceAdapter, FakeClaimExtractionPort, FakeSlackRenderer

listeners/            # Thin Bolt boundary — delegate to TruthExpiryPipeline only
agent/                # Deferred live LLM extraction (NotImplementedError in M0)

app.py                # Socket Mode entrypoint
```

**Listeners must not contain business logic.** They parse Slack events, build `TruthExpiryRequest`, call `get_pipeline().handle()`, and render the response.

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

## Ports and adapters (M0)

| Port | M0 implementation |
|------|-------------------|
| `RtsPort` | `FakeRtsPort` |
| `LifecycleEvidencePort` | `FakeLifecycleEvidenceAdapter` |
| `ClaimExtractionPort` | `FakeClaimExtractionPort` |
| `ClockPort` | `SystemClock` |

Composition: `adapters/composition.py`. Set `TRUTH_EXPIRY_USE_FAKES=1` for local fake mode. Live adapters raise `LiveAdaptersUnavailableError` until M1/M2.

**Do not use `PYTEST_CURRENT_TEST` in production code.** Inject fakes via explicit DI or `build_pipeline()` in tests.

## Slack MCP

**Disabled in M0.** Do not add `MCPServerStreamableHTTP` to the agent. RTS discovery stays application-controlled through `RtsPort`. Use direct Slack Web API for rendering.

## RTS planning (M2 — document only until implemented)

When live RTS is added:

1. Call `assistant.search.info`.
2. Read `is_ai_search_enabled`.
3. Use natural-language question when semantic search is available.
4. Use `disable_semantic_search=True` for explicit keyword fallback.
5. Pass event `action_token` when using bot token.
6. Limit searches per user request.
7. Treat returned content as ephemeral.
8. Preserve source permalinks for display without storing message content.

## Environment variables

| Variable | When | Purpose |
|----------|------|---------|
| `SLACK_BOT_TOKEN` | Slack runs | Bot token |
| `SLACK_APP_TOKEN` | Socket Mode | App-level token |
| `TRUTH_EXPIRY_USE_FAKES=1` | M0 local | Enable fake adapter composition |
| `TRUTH_EXPIRY_LIFECYCLE_MCP_URL` | M1 | Streamable HTTP lifecycle MCP |
| `TRUTH_EXPIRY_LOG_LEVEL` | Optional | Default `INFO`; never log message text |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | Post-M0 live LLM | Claim extraction only |

Document secrets in `.env.sample`. Never commit `.env` or tokens.

## Commands

From repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install ".[dev]"

ruff check .
ruff format --check .
mypy truthexpiry adapters listeners agent
pytest -q
pip-audit -r requirements.txt
```

Local Slack run (optional, not required for M0 CI):

```powershell
$env:TRUTH_EXPIRY_USE_FAKES = "1"
python app.py
```

## What not to commit

- `.cursor/`, `.claude/`, `.slack/`, `.env`, `data/` (OAuth installs)
- `scaffold/` or duplicate template trees
- Slack message text in fixtures or snapshots
- API keys or tokens

## Related docs

- [`REVIEW.md`](REVIEW.md) — pre-merge review checklist
- [`README.md`](README.md) — user-facing overview
- [`docs/SCAFFOLD_INSPECTION.md`](docs/SCAFFOLD_INSPECTION.md) — upstream scaffold inventory
