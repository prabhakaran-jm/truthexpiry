# TruthExpiry — review checklist

Use this before merging changes, opening a PR, or marking a milestone complete.

## Architecture and scope

- [ ] Changes match the current milestone (M0 = fakes only unless explicitly extending M1/M2).
- [ ] Domain logic lives in `truthexpiry/`, not in `listeners/` or `agent/`.
- [ ] New I/O goes behind a port in `truthexpiry/ports/` with an adapter implementation.
- [ ] Listeners only parse events, build `TruthExpiryRequest`, call the pipeline, and render output.

## Deterministic labeling

- [ ] Status labels are assigned only in `truthexpiry/services/labeler.py` (or tests of it).
- [ ] No code path lets the LLM or an unstructured prompt choose `CURRENT`, `SUPERSEDED`, `CONFLICTING`, or `UNVERIFIED`.
- [ ] Supersession requires lifecycle evidence — not message timestamps alone.
- [ ] `CONFLICTING` surfaces both authoritative sources when precedence does not resolve them.
- [ ] Claim keys use `entity|attribute|scope=...` — not permalinks or ticket IDs as identity.

## No Slack content retention

- [ ] No module persists RTS text, retrieved messages, or LLM turns containing Slack content.
- [ ] No `conversation_store`, thread history store, or disk cache of message bodies.
- [ ] Handler-scoped data is discarded after the Slack response is sent.
- [ ] Logs and error reports do not include user message text or search hit bodies.
- [ ] Test fixtures use synthetic metadata (`example.invalid` permalinks, invented IDs) — not real Slack exports.

## RTS and search (when touching search code)

- [ ] M0 uses `FakeRtsPort` only; no `assistant.search.*` calls in tests or default startup.
- [ ] M2 live path will call `assistant.search.info` before `assistant.search.context`.
- [ ] Semantic vs keyword fallback follows `search_plan.py` capabilities.
- [ ] `action_token` from the triggering event is passed when using bot token (M2).
- [ ] Sanitizer strips or avoids retaining raw message bodies beyond the request scope.

## Slack MCP and OAuth

- [ ] No `MCPServerStreamableHTTP` or `https://mcp.slack.com/mcp` in M0 code paths.
- [ ] `manifest.json` keeps `is_mcp_enabled: false` for M0.
- [ ] MVP manifest uses bot `search:read.public` — no user OAuth scopes for private search.
- [ ] App Home and copy do not promise private-channel or DM search in MVP.

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
- [ ] `mypy truthexpiry adapters listeners agent` passes when typing is in scope for the milestone.

## Git hygiene

- [ ] No `scaffold/` directory committed.
- [ ] `.cursor/`, `.claude/`, `.slack/`, `data/` not staged.
- [ ] Commits are focused; unrelated refactors split out when possible.

## Quick verification commands

```powershell
ruff check .
ruff format --check .
mypy truthexpiry adapters listeners agent
pytest -q
pip-audit -r requirements.txt
git grep -E "xox[baprs]-|sk-[A-Za-z0-9]{10,}|ANTHROPIC_API_KEY=\S+|OPENAI_API_KEY=\S+" -- ":!*.sample" ":!.env.sample"
```

Optional local bot smoke (not CI-gated for M0):

```powershell
$env:TRUTH_EXPIRY_USE_FAKES = "1"
python app.py
```
