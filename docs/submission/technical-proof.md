# TruthExpiry technical proof

Factual, verification-oriented record for judges and technical reviewers. This is not marketing copy.

## Submission freeze identity

| Field | Value |
|-------|-------|
| Final commit SHA | `<FINAL_COMMIT_SHA>` |
| Final tag | `<FINAL_TAG>` |
| Recording commit SHA | `<RECORDING_COMMIT_SHA>` |
| Recording profile | `live` / `backup-a` / `backup-b` |
| Recording date | `<RECORDING_DATE>` |
| Repository URL | `<REPOSITORY_URL>` |
| Demo video URL | `<DEMO_VIDEO_URL>` |

**Current development baseline (M5 Commit 2):**

| Field | Value |
|-------|-------|
| M4 release tag | `v0.4.0` → `c3467de` |
| M5 branch | `feat/m5-hackathon-submission` |
| M5 Commit 1 | `1830ddc` — demo preflight and acceptance package |

`<FINAL_TAG>` (for example `v1.0.0`) does **not** exist yet.

## Core technical claim

1. **Slack search retrieves evidence** — one `assistant.search.context` call per request searches **public channels** only.
2. **OpenAI extracts zero or one structured claim** — strict schema; no validity labels in model output.
3. **Deterministic code grounds and validates** — query-value grounding, claim-schema validation, evidence-ID mapping.
4. **Lifecycle MCP returns lifecycle evidence** — read-only synthetic records via bearer-authenticated MCP transport.
5. **Deterministic labeler assigns validity** — `CURRENT`, `SUPERSEDED`, `CONFLICTING`, `UNVERIFIED` are computed in `truthexpiry/services/labeler.py` only.

Architecture source: [`docs/architecture/truthexpiry-architecture.mmd`](../architecture/truthexpiry-architecture.mmd)

## Deterministic authority boundary

| Responsibility | Repository area |
|----------------|-----------------|
| Claim schema catalog | `truthexpiry/services/claim_schema.py` |
| Query-value grounding | `truthexpiry/services/query_grounding.py` |
| Null-model query fallback | `truthexpiry/services/query_claim_fallback.py` |
| Evidence-ID and DTO validation | `adapters/llm/adapter.py`, `adapters/llm/contracts.py` |
| Lifecycle evidence fetch | `adapters/lifecycle_mcp/adapter.py` |
| Validity labeling | `truthexpiry/services/labeler.py` |

The LLM (`agent/extraction_agent.py`, model `openai:gpt-4.1-mini`) extracts structured claims only. It does not call lifecycle tools and does not assign validity.

## Slack integration evidence

| Property | Implementation |
|----------|----------------|
| Event delivery | Slack Socket Mode (`truthexpiry/ops/socket_mode.py`) |
| Supported triggers | App mentions (`listeners/events/app_mentioned.py`); DMs (`listeners/events/message.py`) |
| Evidence API | `assistant.search.context` via `adapters/slack_rts/` |
| Channel scope | `channel_types: ["public_channel"]` only |
| RTS calls per request | One |
| Action token | Request-scoped; forwarded by listeners; required by live RTS adapter; never logged |
| Private-channel exclusion | No private/DM/MPDM search in MVP payload |

## Extraction safety evidence

| Property | Value |
|----------|-------|
| Structured output | `ClaimExtractionOutputDto` with `claim: null` or one claim object |
| Claims per request | Zero or one |
| Evidence grounding | Opaque `evidence-N` IDs mapped to sanitized refs in adapter |
| Query-value grounding | Rejects model claims whose `stated_value` is not grounded in query text |
| Informational queries | No structured claim (for example “Tell me about report export…”) |
| Conflicting polarity | No structured claim when query supports multiple polarities |
| OpenAI model | `openai:gpt-4.1-mini` (fixed in `agent/extraction_agent.py`) |
| Provider timeout | 20 seconds (`adapters/llm/runner.py`) |
| Retries | Disabled (`retries=0` on extraction agent) |
| Sent to OpenAI | Bounded user query; up to 8 hits; truncated message text with opaque evidence IDs |
| Never sent to OpenAI | Lifecycle records; validity labels; Slack tokens; conversation history |

## Lifecycle evidence

Synthetic dataset: `lifecycle_mcp/data/lifecycle_records.json` (read-only at request time).

### PROD-482

| Field | Value |
|-------|-------|
| Entity / attribute | `report_export` / `availability` |
| Canonical value | `disabled` |
| State | `SHIPPED` |
| Effective date | `2026-05-12` |
| Supersedes | `PROD-481` (`enabled`) |

**Demo meaning:** query asks **available** → **SUPERSEDED**; query asks **disabled** → **CURRENT**.

### PROD-511

| Field | Value |
|-------|-------|
| Entity / attribute | `api_rate_limit` / `max_requests` |
| Canonical value | `50` |
| State | `SHIPPED` |
| Effective date | `2024-06-01` |
| Supersedes | `PROD-510` (`100`) |

**Demo meaning:** query states **100** → **SUPERSEDED**; query states **50** → **CURRENT**.

## Operational evidence

| Property | Implementation |
|----------|----------------|
| Services | Independent worker (`app.py`) and lifecycle MCP (`lifecycle_mcp/server.py`) |
| MCP authentication | Shared bearer token on MCP transport (`lifecycle_mcp/bearer_auth.py`); token not in URL |
| Worker liveness | `GET /healthz` → 200 while process up |
| Worker readiness | `GET /readyz` → 200 when configuration, Socket Mode, and MCP checks pass |
| MCP liveness / readiness | `GET /healthz` / `GET /readyz` on MCP health port |
| MCP outage | Worker remains live; `/readyz` → 503; recovers without worker restart (`truthexpiry/ops/mcp_health.py`) |
| Graceful shutdown | SIGTERM/SIGINT → draining → 503 readiness → intake close → in-flight drain |
| Logging | Structured JSON option; bounded fields; no raw query or message bodies |
| Metrics | Optional counters/histograms with bounded labels (`truthexpiry/ops/metrics.py`) |
| Event deduplication | Optional `TRUTH_EXPIRY_DEDUP_EVENT_IDS=1` |
| Containers | Multi-stage wheel Dockerfiles; runtime UID 10001 |

## Automated verification

Values below were collected **locally during M5 Commit 2** on branch `feat/m5-hackathon-submission` unless noted.

| Check | Result | Source |
|-------|--------|--------|
| Collected tests | 494 | `pytest --collect-only -q` (local) |
| Unit + integration run | 493 passed, 1 skipped, 3 warnings | `pytest -q` (local) |
| Integration tests | 11 passed | `pytest -q tests/integration/` (local) |
| Demo preflight tests | 41 passed, 1 skipped | `pytest -q tests/unit/test_demo_preflight.py` (local) |
| Ruff lint | Pass | `ruff check .` (local) |
| Ruff format | Pass | `ruff format --check .` (local) |
| Mypy | Pass (102 source files) | `mypy truthexpiry adapters lifecycle_mcp listeners agent scripts` (local) |
| pip-audit | No known vulnerabilities | `pip-audit -r requirements.txt` (local) |
| Structural checks | OK | `python app.py --check`; `python -m lifecycle_mcp.server --check` (local) |
| Preflight backup-b | Pass on clean tree | `python scripts/demo_preflight.py --profile backup-b` (local) |

### CI workflows (repository configuration)

| Workflow file | Name |
|---------------|------|
| `.github/workflows/tests.yml` | Run all the unit tests |
| `.github/workflows/ruff.yml` | Linting and formatting validation using ruff |
| `.github/workflows/security.yml` | Security dependency audit |
| `.github/workflows/containers.yml` | Container build smoke |
| `.github/workflows/dependencies.yml` | Merge updates to dependencies |

CI pass/fail for a specific commit is reported by GitHub Actions on the branch — not re-asserted here without a workflow run URL.

### Manual / live acceptance

Final product and operational rows are recorded in [`docs/demo/live-acceptance.md`](../demo/live-acceptance.md). **Rows remain unsigned** until executed on the final M5 commit.

## Independent review history

Established milestone outcomes documented in this repository:

| Milestone | Outcome |
|-----------|---------|
| **M2** | Live public-channel RTS integrated; manual acceptance scenarios documented in [`docs/MILESTONE_2.md`](../MILESTONE_2.md) |
| **M3** | Live OpenAI extraction integrated; manual acceptance queries documented in [`docs/MILESTONE_3.md`](../MILESTONE_3.md) |
| **M4** | Operational hardening merged via PR #4; tag `v0.4.0`; outage recovery and container CI fixes on `master` |

**M5** has not completed independent review or signed live acceptance at the time of this document.

## Privacy invariants

- Public Slack evidence only for workspace search.
- No private-channel search in RTS payload.
- No persistence of Slack message bodies across requests.
- No raw prompts or provider outputs in application logs.
- Health/readiness JSON excludes secrets and message content.
- Metrics use bounded labels only (no high-cardinality query or user labels).
- MCP bearer token is a header value, not embedded in URLs.
- Demo preflight prints variable names and safe states only ([`docs/demo/preflight.md`](../demo/preflight.md)).

## Final acceptance record

Complete the matrix in [`docs/demo/live-acceptance.md`](../demo/live-acceptance.md) after final recording.

Do **not** paste Slack message bodies, tokens, prompts, model output, or private-channel content into acceptance notes.

## Known non-blocking items

| Item | Notes |
|------|-------|
| Pydantic AI deprecation warning | `openai:` model string deprecation warning at pinned `pydantic-ai==1.107.0` (observed in unit tests) |
| Cloud deployment platform | Not selected; local and container smoke documented in M4 |
| Final media URLs | `<DEMO_VIDEO_URL>` and screenshot assets pending M5 media commits |
| Final release tag | `<FINAL_TAG>` not created |
