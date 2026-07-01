# TruthExpiry — review checklist

Use this before merging changes, opening a PR, or marking a milestone complete.

## Architecture and scope

- [ ] Changes match the current milestone (M4 = operational hardening on top of M3 extraction + M2 RTS + lifecycle MCP).
- [ ] Domain logic lives in `truthexpiry/`, not in `listeners/` or `agent/`.
- [ ] New I/O goes behind a port in `truthexpiry/ports/` with an adapter implementation.
- [ ] Listeners only parse events, build `TruthExpiryRequest`, call the pipeline, and render output.

## Deterministic labeling

- [ ] Status labels are assigned only in `truthexpiry/services/labeler.py` (or tests of it).
- [ ] No code path lets the LLM or an unstructured prompt choose `CURRENT`, `SUPERSEDED`, `CONFLICTING`, or `UNVERIFIED`.
- [ ] Supersession requires lifecycle evidence — not message timestamps alone.
- [ ] `CONFLICTING` surfaces both authoritative sources when precedence does not resolve them.
- [ ] `UNVERIFIED` distinguishes empty evidence from MCP unavailable (fail-closed) when lifecycle adapter changes.
- [ ] Claim keys use `entity|attribute|scope=...` — not permalinks or ticket IDs as identity.

## No Slack content retention

- [ ] No module persists RTS text, retrieved messages, or LLM turns containing Slack content.
- [ ] No `conversation_store`, thread history store, or disk cache of message bodies.
- [ ] Handler-scoped data is discarded after the Slack response is sent.
- [ ] Logs and error reports do not include user message text or search hit bodies.
- [ ] Test fixtures use synthetic metadata (`example.invalid` permalinks, invented IDs) — not real Slack exports.

## RTS and search (when touching search code)

- [ ] M0/M1 use `FakeRtsPort` in all-fake mode; no `assistant.search.info` in production request paths.
- [ ] M2 live path makes one `assistant.search.context` call per invocation with `disable_semantic_search=False`.
- [ ] `action_token` is forwarded by listeners and validated only in `SlackRtsAdapter`; excluded from repr and logs.
- [ ] Ticket extraction happens in `rts_sanitizer.py`, not the Slack mapper.
- [ ] Sanitizer and pipeline discard ephemeral hit content after the request; evidence refs are metadata only.

## Slack MCP and OAuth

- [ ] No `MCPServerStreamableHTTP` or `https://mcp.slack.com/mcp` in M0 code paths.
- [ ] `manifest.json` keeps `is_mcp_enabled: false` for M0.
- [ ] MVP manifest uses bot `search:read.public` — no user OAuth scopes for private search.
- [ ] App Home and copy do not promise private-channel or DM search in MVP.

## Lifecycle MCP (M1)

- [ ] MCP server is read-only; tool `get_lifecycle_evidence` uses flat `entity` / `attribute` / `scope` args only.
- [ ] Server does not assign `CURRENT`, `SUPERSEDED`, `CONFLICTING`, or `UNVERIFIED`.
- [ ] Client adapter reads `structuredContent` only — never plain-text `content`.
- [ ] `lifecycle_mcp/data/lifecycle_records.json` is synthetic invented data; no real Slack content.
- [ ] Server binds `127.0.0.1` by default; not documented as production-ready.
- [ ] `TRUTH_EXPIRY_LIFECYCLE_MCP_URL` (client) is separate from `TRUTH_EXPIRY_LIFECYCLE_MCP_HOST` / `PORT` (server).
- [ ] Subprocess transport integration test passes: `pytest -q tests/integration/test_lifecycle_mcp_transport.py`.
- [ ] M2 exclusions respected: no private search, pagination, live LLM, OAuth, Slack MCP, or lifecycle/labeler changes.

## Slack RTS (M2)

- [ ] `SlackRtsAdapter` uses `api_call("assistant.search.context")` only — no generated SDK convenience method.
- [ ] Public-channel-only payload (`channel_types`, `content_types`) locked by unit tests.
- [ ] Empty RTS results return an honest user message without fake claim fallback.
- [ ] RTS failures raise `RtsSearchUnavailableError` and fail closed.
- [ ] Documentation states RTS eligibility (internal / directory-published apps).
- [ ] `caplog` tests prove sensitive values are not logged.

## Live claim extraction (M3)

- [ ] `TRUTH_EXPIRY_CLAIM_EXTRACTOR=fake|live` is independent of RTS/lifecycle selection.
- [ ] `TRUTH_EXPIRY_USE_FAKES=1` overrides selector unless `llm` is explicitly injected.
- [ ] Live extractor requires `OPENAI_API_KEY`; Anthropic key alone does not enable live mode.
- [ ] Structured output uses `extra="forbid"`; `claim` is always present (`null` for no claim).
- [ ] Model schema excludes validity labels, permalinks, and lifecycle ticket IDs.
- [ ] Domain `claim_schema` catalog owns required scope keys — not the model.
- [ ] Evidence IDs are opaque (`evidence-N`); adapter maps to sanitized refs only.
- [ ] Query length > 500 and provider failures fail closed with generic unavailable message.
- [ ] Fixed 20s timeout; no automatic retry in M3.
- [ ] Tests use `tests/fakes/extraction_runner.py` — no production network calls.
- [ ] M3 exclusions respected: no RTS, lifecycle, labeler, OAuth, or deployment changes.

## Operational hardening (M4)

- [ ] Configuration uses `truthexpiry/config/` (`from_env` vs `validate_runtime` vs `validate_for_composition`); secrets redacted in `repr`/`str()` and `ConfigError` messages.
- [ ] `python app.py --check` and `python -m lifecycle_mcp.server --check` succeed without live credentials.
- [ ] Worker `/healthz` returns 200 while process is up; `/readyz` returns 503 until Socket Mode and live dependencies are ready.
- [ ] MCP `/healthz` and `/readyz` on `TRUTH_EXPIRY_LIFECYCLE_MCP_HEALTH_PORT` do not leak tokens or dataset bodies.
- [ ] Bearer auth on MCP `/mcp` when auth enabled; `TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_DISABLED=1` only for local dev/tests.
- [ ] SIGTERM/SIGINT triggers shutdown drain; handler rejects new requests when draining.
- [ ] JSON logs (`TRUTH_EXPIRY_LOG_FORMAT=json`) include `event`, `outcome`, `duration_ms`, `query_length`, `claim_count`, `evidence_count`, `correlation_id` — never raw query text or tokens.
- [ ] Metrics labels limited to `service`, `outcome`, `failure_category`; `/metrics` exposes counters when `TRUTH_EXPIRY_METRICS_ENABLED=1`.
- [ ] `Dockerfile` and `Dockerfile.lifecycle-mcp` build; `.github/workflows/containers.yml` passes on PRs.
- [ ] Worker MCP startup polls MCP HTTP `/readyz` via background monitor; temporary MCP outage does not exit the worker.
- [ ] Runtime MCP outage degrades worker `/readyz` to 503 and recovers without restart.
- [ ] Worker `draining=yes` makes `/readyz` 503 immediately; `/healthz` stays 200.
- [ ] Socket Mode disconnect reports `disconnected` (not `connecting`) after first connection.
- [ ] MCP readiness includes `tool_registration=ok` after tool registration.
- [ ] MCP `/readyz` on health port is unauthenticated and private-network only; `/mcp` requires bearer when auth enabled.
- [ ] Production images install from wheels (non-editable); runtime UID 10001.
- [ ] M4 exclusions respected: no RTS payload, extraction, labeler, or lifecycle tool contract changes.

## Secrets and dependencies

- [ ] No tokens, API keys, or `.env` contents in committed files.
- [ ] `.env.sample` documents variables without real values.
- [ ] `pip-audit` and secret grep (see `AGENTS.md`) pass on changed branches.
- [ ] No new dependencies without justification; dev tools belong in `[dev]` extras.

## Tests and CI

- [ ] `pytest -q` passes without Slack, LLM, or MCP credentials.
- [ ] Fakes injected via `conftest` or explicit `build_pipeline(...)` — not env detection hacks like `PYTEST_CURRENT_TEST` in production code.
- [ ] Unit tests cover labeler edge cases for all four statuses when labeler changes.
- [ ] `ruff check .` and `ruff format --check .` pass.
- [ ] `mypy truthexpiry adapters lifecycle_mcp listeners agent` passes when typing is in scope for the milestone.

## Git hygiene

- [ ] No `scaffold/` directory committed.
- [ ] `.cursor/`, `.claude/`, `.slack/`, `data/` not staged.
- [ ] Commits are focused; unrelated refactors split out when possible.

## Milestone 5 (demo and submission)

- [ ] Demo preflight is read-only and never prints secret values or response bodies.
- [ ] `python scripts/demo_preflight.py --profile backup-b` passes on a clean tree before recording prep.
- [ ] Live acceptance matrix in [docs/demo/live-acceptance.md](docs/demo/live-acceptance.md) completed with safe notes only.
- [ ] Architecture Mermaid source in [docs/architecture/truthexpiry-architecture.mmd](docs/architecture/truthexpiry-architecture.mmd) matches product boundaries (LLM does not assign validity).
- [ ] Technical proof in [docs/submission/technical-proof.md](docs/submission/technical-proof.md) uses placeholders only — no fabricated URLs or unsigned acceptance claims.
- [ ] M5 changes do not modify frozen product paths (`adapters/slack_rts/`, `adapters/llm/`, labeler, query grounding, lifecycle JSON).
- [ ] Backup demo modes are disclosed when used (`backup-a`, `backup-b`).

## Quick verification commands

```powershell
ruff check .
ruff format --check .
mypy truthexpiry adapters lifecycle_mcp listeners agent
pytest -q
pytest -q tests/integration/test_lifecycle_mcp_transport.py
pytest -q tests/integration/test_deployment_smoke.py
pip-audit -r requirements.txt
git diff --check
git grep -E "xox[baprs]-|sk-[A-Za-z0-9]{10,}|ANTHROPIC_API_KEY=\S+|OPENAI_API_KEY=\S+" -- ":!*.sample" ":!.env.sample"
```

Optional local smoke (not CI-gated):

```powershell
# All-fake Slack app
$env:TRUTH_EXPIRY_USE_FAKES = "1"
python app.py

# Lifecycle MCP server + client smoke
python -m lifecycle_mcp.server
python -m lifecycle_mcp.smoke --url http://127.0.0.1:8000/mcp
```
