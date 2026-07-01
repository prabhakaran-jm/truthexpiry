# TruthExpiry — hackathon submission copy

Reusable, factual copy for Devpost or similar platforms. Paste into fields after confirming each platform's character limits. Replace placeholders before submitting.

**Related documents:** [technical-proof.md](technical-proof.md) · [live acceptance](../demo/live-acceptance.md) · [preflight](../demo/preflight.md) · [architecture source](../architecture/truthexpiry-architecture.mmd) · [README](../../README.md) · [LICENSE](../../LICENSE)

---

## Table of contents

1. [Submission identity](#1-submission-identity)
2. [Tagline options](#2-tagline-options)
3. [One-sentence pitch](#3-one-sentence-pitch)
4. [Short summary variants](#4-short-summary-variants)
5. [Full project description](#5-full-project-description)
6. [Common platform fields](#6-common-platform-fields)
7. [Why Slack](#7-why-slack)
8. [Slack features and APIs used](#8-slack-features-and-apis-used)
9. [Architecture summary](#9-architecture-summary)
10. [Technologies used](#10-technologies-used)
11. [Security and privacy answer](#11-security-and-privacy-answer)
12. [Demo script synopsis](#12-demo-script-synopsis)
13. [Limitations](#13-limitations)
14. [Team placeholders](#14-team-placeholders)
15. [Final submission checklist](#15-final-submission-checklist)
16. [Verification appendix](#16-verification-appendix)

---

## 1. Submission identity

| Field | Value |
| --- | --- |
| Project name | TruthExpiry |
| Tagline | See [section 2](#2-tagline-options) — recommended: **Similarity is not validity.** |
| Category / track | `<HACKATHON_TRACK>` |
| Repository | `https://github.com/prabhakaran-jm/truthexpiry` |
| Demo video | `<DEMO_VIDEO_URL>` |
| Live deployment | Not applicable — judges use the **Slack Developer sandbox** with seeded `#truthexpiry-demo` |
| Final commit | `<FINAL_COMMIT_SHA>` (draft: `6f85cb1` at M5+P1 copy freeze) |
| Final tag | `<FINAL_TAG>` |
| Team | `<TEAM_NAME>` |
| Team members | `<TEAM_MEMBER_NAMES_AND_ROLES>` |

No live deployment is claimed at the time of this document. `<FINAL_TAG>` (for example `v1.0.0`) does not exist yet. M4 release tag `v0.4.0` points to commit `c3467de`.

---

## 2. Tagline options

| # | Tagline |
| --- | --- |
| A | **Similarity is not validity.** |
| B | Lifecycle-aware Slack evidence with deterministic validation. |
| C | Search Slack. Extract a claim. Let code decide if it still holds. |

**Recommended primary tagline:** **A — Similarity is not validity.**

---

## 3. One-sentence pitch

TruthExpiry searches **public Slack evidence**, uses OpenAI to extract **zero or one structured claim**, checks it against **lifecycle records** via an authenticated MCP service, and **deterministically** tells users whether the claim is **current**, **superseded**, **conflicting**, or **unverified**.

---

## 4. Short summary variants

Word counts use whitespace-separated tokens (same method as [section 16](#16-verification-appendix)).

### ~25 words (actual: **23**)

TruthExpiry searches public Slack evidence, extracts one structured claim with OpenAI, checks lifecycle records, and deterministically labels it current, superseded, conflicting, or unverified.

### ~50 words (actual: **45**)

TruthExpiry is a Slack agent that searches public workspace messages, uses OpenAI to extract zero or one structured claim, and validates it against bearer-authenticated lifecycle records. Deterministic code—not the model—assigns CURRENT, SUPERSEDED, CONFLICTING, or UNVERIFIED. Similarity is not validity; obsolete messages can still sound convincing.

### ~100 words (actual: **91**)

Teams ask questions in Slack where old decisions still sound relevant. TruthExpiry answers by searching public channel evidence with `assistant.search.context`, extracting zero or one structured claim through OpenAI, and validating it against lifecycle records through a bearer-authenticated MCP service. Deterministic grounding, schema checks, and a labeler assign CURRENT, SUPERSEDED, CONFLICTING, or UNVERIFIED. The model never decides validity. Users may invoke the app from a DM, but evidence search remains public-channel-only. No Slack message bodies are persisted across requests. One RTS call is made per invocation. Failures fail closed without inventing claims.

### ~150 words (actual: **144**)

TruthExpiry prevents Slack agents from repeating stale organizational memory. When a user mentions the app or sends a direct message, Socket Mode delivers the event, public Slack evidence is retrieved with one `assistant.search.context` call per request, and OpenAI extracts zero or one structured claim using opaque evidence IDs. Deterministic code grounds the claim against the query, validates the schema, fetches lifecycle evidence from an independently deployable MCP server, and assigns CURRENT, SUPERSEDED, CONFLICTING, or UNVERIFIED. Informational or ambiguous queries produce no invented claim. Similarity is not validity: a semantically similar message may already be superseded. The project enforces privacy boundaries—public evidence only, no message persistence, redacted secrets, bounded operational logs and metrics, and preflight checks that never print secret values. Live extraction uses a fixed OpenAI model with retries disabled. Bearer authentication protects the lifecycle MCP transport. Health endpoints expose bounded operational state only.

---

## 5. Full project description

**Word count: 543**

### Problem

Teams increasingly ask operational questions inside Slack. Workspace search and agent tools can surface messages that *sound* like answers because they are semantically similar to the question. That similarity does not establish whether the statement is still valid. Policies change, features ship, limits are revised, and older messages remain searchable long after they have been superseded. A message that matched yesterday’s understanding can mislead today’s decision. Without a separate validity layer grounded in lifecycle records, users can act on obsolete guidance that still reads convincingly in context.

### Solution

TruthExpiry is a Slack-native agent that connects **what people said in public channels** with **what lifecycle records say today**. It retrieves candidate evidence from Slack, extracts a concrete structured claim, checks authoritative lifecycle data, and returns a clear validity result—without asking users to leave Slack or trust semantic similarity alone.

### How it works

1. A user invokes TruthExpiry through an **app mention** or **direct message**.
2. **Socket Mode** delivers the event to the TruthExpiry worker.
3. **`assistant.search.context`** searches **public Slack messages** (one RTS call per request).
4. **OpenAI** (`openai:gpt-4.1-mini`) extracts **zero or one** structured claim using opaque evidence IDs.
5. **Deterministic grounding and schema validation** reject unsupported, ungrounded, or ambiguous claims.
6. The **lifecycle MCP** service returns read-only lifecycle records over **bearer-authenticated** transport.
7. The **deterministic labeler** assigns **CURRENT**, **SUPERSEDED**, **CONFLICTING**, or **UNVERIFIED**.
8. TruthExpiry replies in Slack with a concise result and evidence references.

There is no cross-turn conversation memory and no durable store of Slack message bodies. Each request is handled independently.

### Technical differentiator

**The model extracts. It never decides validity.**

OpenAI performs probabilistic structured extraction only: zero or one claim per request, fixed model, 20-second timeout, retries disabled. Lifecycle records are not sent to OpenAI. Deterministic code owns query-value grounding, claim-schema validation, evidence-ID mapping, lifecycle interpretation, and label assignment. When extraction or evidence is unavailable, the system fails closed with generic user-facing messages rather than guessing.

### Demonstrated examples

Synthetic lifecycle dataset scenarios confirmed in the repository:

| Query theme | Expected result | Lifecycle proof |
| --- | --- | --- |
| Report export **available** on Starter | **SUPERSEDED** | PROD-482 (`disabled` supersedes `enabled`) |
| Report export **disabled** on Starter | **CURRENT** | PROD-482 |
| Informational report-export question | Guidance — supported topics listed | No validity label invented |
| API limit **100 requests** for Starter | **SUPERSEDED** | PROD-511 (`50` supersedes `100`) |
| API limit **50 requests** for Starter | **CURRENT** | PROD-511 |
| Analytics export / refund / mobile push / feature flags / legacy API | Valid when query states one explicit claim in catalog | See expanded seed messages |

Judges can explore **seven claim families** in the sandbox. Block Kit responses show status, Slack permalinks, and lifecycle timeline IDs (PROD-*).

### Operational design

TruthExpiry runs as two independently deployable services: a **Slack Socket Mode worker** and a **lifecycle MCP HTTP server**. Each exposes `/healthz` (liveness) and `/readyz` (readiness). During a temporary MCP outage the worker stays live but unready; readiness recovers without restarting the worker. Graceful shutdown drains in-flight requests before exit. Structured logging and optional bounded metrics avoid leaking queries, evidence, or secrets. Production container images use multi-stage wheel installs and run as non-root user `truthexpiry` (UID 10001). Demo preflight tooling verifies readiness without printing credentials.

### Privacy and safety

- **Public Slack evidence only** for workspace search.
- A user may invoke from a **DM**, but **DM and private-channel history are not searched**.
- **No persistence** of Slack message bodies across requests.
- **Opaque request-local evidence IDs** in the extraction prompt; lifecycle records stay out of OpenAI.
- Operational logs exclude raw queries, evidence text, tokens, prompts, and provider output.
- Demo **preflight** checks secret presence without printing values.

### Outcome

TruthExpiry helps users understand whether a retrieved statement **still matches lifecycle reality**, whether it has been **superseded**, whether **authoritative sources conflict**, or whether the system lacks enough lifecycle evidence to decide. It does not claim to establish universal factual truth outside the configured lifecycle evidence scope. The goal is actionable clarity inside Slack—not a score of absolute correctness for every possible question.

---

## 6. Common platform fields

### Inspiration

The most similar memory in a workspace may be the one that is already obsolete. We built TruthExpiry to separate semantic retrieval from temporal validity—so Slack agents can cite evidence without treating similarity as proof.

### What it does

TruthExpiry answers questions in Slack by searching public channel evidence, extracting a structured claim, checking lifecycle records, and returning a deterministic validity label.

### How we built it

Python application built on **Slack Bolt** with **Socket Mode** event delivery. Public evidence comes from Slack **`assistant.search.context`**. Claim extraction uses **Pydantic AI** with **OpenAI** structured output. Lifecycle evidence is served by a read-only **MCP** server with bearer authentication. Deterministic **claim-schema**, **query grounding**, and **labeler** modules assign validity. **Docker** images and **GitHub Actions** support repeatable verification.

### Challenges we ran into

- Extracting a claim **without letting the model invent** stated values or validity labels.
- Separating **semantic similarity** from **lifecycle validity**.
- Grounding model output to **opaque evidence IDs** and query text.
- Handling **request-scoped Slack action tokens** safely for live RTS.
- Keeping a Socket Mode worker **alive but unready** during MCP outage instead of crash-looping.
- Ensuring **logs, metrics, and health endpoints** never leak Slack content or secrets.

### Accomplishments we are proud of

- Clear **deterministic validity authority** — the model never assigns CURRENT, SUPERSEDED, CONFLICTING, or UNVERIFIED.
- **Public-channel-only** Slack search with one RTS call per request.
- Strict **zero-or-one** structured extraction with fail-closed grounding.
- **Independently deployable**, bearer-authenticated lifecycle MCP service.
- **MCP outage recovery** without worker restart.
- **Block Kit** verdict layout with lifecycle timeline and Slack permalinks.
- **Judge-ready sandbox** — seeded public evidence, seven claim families, suggested prompts.
- Extensive **automated test suite** (511+ tests) and documented milestone reviews (see [technical-proof.md](technical-proof.md)).

At the latest local freeze, the repository passed **511 automated tests** (1 skipped) and **11 integration tests** with `pytest -q` and `pytest -q tests/integration/`.

### What we learned

- Retrieval relevance is not the same as temporal validity.
- LLM authority must be constrained to structured extraction.
- Slack **action-token** lifecycle matters for live RTS.
- Operational readiness should degrade gracefully without restart loops.
- Privacy must be enforced in logs, metrics, health responses, and demo tooling—not only in prompts.

### What is next

- Replace the synthetic lifecycle dataset with integrations to issue trackers, release systems, policy registries, or feature-flag sources.
- Pagination and broader RTS evidence handling.
- Configurable schema catalogs beyond the demo catalog.
- Administrative lifecycle-record management (out of scope today).
- Durable event deduplication beyond optional in-memory mode.
- Deployment templates once a cloud platform is selected.
- Richer explanations when lifecycle sources conflict.

---

## 7. Why Slack

Organizational memory already lives in Slack. Users should not need to leave the conversation to ask whether a retrieved statement still holds. **App mentions** and **direct messages** provide a natural interaction surface, while **`assistant.search.context`** supplies public workspace evidence at question time. TruthExpiry adds the missing **temporal validity layer** on top of search: lifecycle records decide whether similar evidence is still current. The **public-only** search boundary keeps the demo scope explicit and privacy-preserving.

---

## 8. Slack features and APIs used

| Feature / API | Role in TruthExpiry |
| --- | --- |
| Slack Bolt for Python | App framework, event handlers, Slack responses |
| Socket Mode | Event delivery to the worker (`SLACK_APP_TOKEN`) |
| App mentions | Primary public-channel entry point |
| Direct-message events | Alternate entry point (search scope remains public) |
| `assistant.search.context` | Public-message evidence retrieval (one call per request) |
| Request-scoped `action_token` | Required for live RTS; forwarded from event; never logged |
| Bot scope `search:read.public` | Public-channel search permission (see `manifest.json`) |
| Slack Web API (`api_call`) | RTS invocation and response posting |

**Not used:** private-channel search, DM/MPDM evidence search, OAuth user-token flows for search, Slack MCP (`mcp.slack.com`), message history persistence, Workflow Builder, canvases, or lists as product dependencies.

---

## 9. Architecture summary

TruthExpiry separates **probabilistic extraction** (OpenAI proposes zero or one structured claim) from **deterministic validation** (grounding, schema checks, lifecycle MCP evidence, label assignment). Operational controls—health/readiness, bearer authentication, outage monitoring, privacy-safe logs—run alongside but do not decide validity.

**Compact flow:**

```text
Slack user → app mention or DM → Socket Mode → assistant.search.context (public evidence)
→ OpenAI structured extraction → deterministic grounding and schema validation
→ lifecycle MCP (bearer auth) → deterministic labeler → Slack response
```

- Full Mermaid source: [`../architecture/truthexpiry-architecture.mmd`](../architecture/truthexpiry-architecture.mmd)
- Verification record: [technical-proof.md](technical-proof.md)

No exported architecture image is committed yet; see [`../assets/README.md`](../assets/README.md) for export guidance.

---

## 10. Technologies used

### Product

| Technology | Confirmed use |
| --- | --- |
| Python | Application language (`pyproject.toml`) |
| Slack Bolt | Event handling and Slack integration |
| Slack Socket Mode | Worker event transport |
| Slack Real-Time Search | `assistant.search.context` adapter |
| Pydantic AI | Structured OpenAI extraction |
| OpenAI | Claim extraction provider (`openai:gpt-4.1-mini`) |
| MCP | Lifecycle evidence transport |

### Validation

| Technology | Confirmed use |
| --- | --- |
| Pydantic models | Structured extraction and config DTOs |
| Deterministic query grounding | `truthexpiry/services/query_grounding.py` |
| Claim-schema catalog | `truthexpiry/services/claim_schema.py` |
| Lifecycle repository | `lifecycle_mcp/data/lifecycle_records.json` |
| Deterministic validity labeler | `truthexpiry/services/labeler.py` |

### Operations

| Technology | Confirmed use |
| --- | --- |
| Docker | `Dockerfile`, `Dockerfile.lifecycle-mcp`, `docker-compose.yml` |
| HTTP health/readiness | `/healthz`, `/readyz` on worker and MCP |
| Structured logging | `TRUTH_EXPIRY_LOG_FORMAT=json` option |
| Bounded metrics | Optional Prometheus-style endpoint |
| GitHub Actions | `.github/workflows/` CI |
| pytest | Automated test suite |
| Ruff | Lint and format |
| mypy | Static typing |
| pip-audit | Dependency vulnerability scan |

---

## 11. Security and privacy answer

TruthExpiry searches **public Slack channel evidence only**. Users may invoke the app from a direct message, but private channels, DMs, and MPDMs are not searched. Slack message bodies are **not persisted** across requests.

Secrets (Slack tokens, OpenAI key, MCP bearer token) are loaded from the environment and **redacted** in configuration representations and error messages. The lifecycle MCP service uses **bearer authentication** on the MCP transport; the token is sent as a header, not embedded in URLs.

Application logs and optional metrics use **bounded fields** and exclude raw user queries, evidence text, prompts, provider output, and high-cardinality identifiers. Health and readiness endpoints return **operational state only**. Container images run as a **non-root** user. Demo preflight verifies secret **presence** without printing values.

These are engineering controls documented in the repository. TruthExpiry does not claim formal penetration testing, SOC 2, GDPR certification, or encryption-at-rest guarantees beyond what the deployment environment provides.

---

## 12. Demo script synopsis

Timed script: [`../demo/recording-script.md`](../demo/recording-script.md) (target **2:50**, hard max **3:00**).

1. **Hook** — “Similarity is not validity.”
2. **Stale report-export claim** — “available” → **SUPERSEDED** (PROD-482) with Block Kit timeline.
3. **Current report-export claim** — “disabled” → **CURRENT** (PROD-482).
4. **Informational query** — guidance with supported claim families; no invented label.
5. **Numeric superseded claim** — “100 requests” → **SUPERSEDED** (PROD-511).
6. **Record-flip beat** — highlight Slack `enabled` vs authoritative **PROD-482** (hero moment).
7. **Close** — judges get a seeded sandbox workspace; model extracts, code decides validity.

**Not in the primary video:** MCP outage recovery (supplementary clip only).

Preflight and acceptance: [`../demo/preflight.md`](../demo/preflight.md), [`../demo/live-acceptance.md`](../demo/live-acceptance.md).

---

## 13. Limitations

Copy-ready limitations answer:

- **Synthetic lifecycle dataset** for the hackathon demo—not a live Jira or policy registry integration.
- **Public Slack evidence only** by design.
- **No cross-turn conversational memory**; each request is independent.
- **Live extraction** depends on OpenAI availability; failures fail closed.
- **Optional event deduplication** is in-memory only—not a durable store.
- **Cloud deployment platform** is not selected; Docker and runbooks are platform-neutral.
- **No administrative UI** for lifecycle-record management.

Privacy boundaries above are intentional scope choices, not defects.

---

## 14. Team placeholders

| Name | Role | Contribution |
| --- | --- | --- |
| `<NAME>` | `<ROLE>` | `<CONTRIBUTION>` |

Replace before submission. Store canonical team string in `<TEAM_NAME>` and `<TEAM_MEMBER_NAMES_AND_ROLES>` in [section 1](#1-submission-identity).

---

## 15. Final submission checklist

Complete before publishing:

- [ ] Platform field character limits checked against [section 4](#4-short-summary-variants) and [section 5](#5-full-project-description)
- [ ] Primary tagline selected ([section 2](#2-tagline-options))
- [ ] `<REPOSITORY_URL>` inserted
- [ ] `<DEMO_VIDEO_URL>` inserted
- [ ] `<LIVE_DEPLOYMENT_URL_OR_NOT_APPLICABLE>` completed (or marked not applicable)
- [ ] `<HACKATHON_TRACK>` inserted
- [ ] `<TEAM_NAME>` and team table ([section 14](#14-team-placeholders)) completed
- [ ] Thumbnail / cover image uploaded
- [ ] `<FINAL_COMMIT_SHA>` and `<FINAL_TAG>` inserted
- [ ] [technical-proof.md](technical-proof.md) finalized for freeze commit
- [ ] [live acceptance](../demo/live-acceptance.md) signed after live demo
- [ ] No placeholder tokens remain in pasted platform fields
- [ ] Backup demo mode disclosed if `backup-a` or `backup-b` used for recording

**Deliberate placeholders in this document:**

`<HACKATHON_TRACK>`, `<REPOSITORY_URL>`, `<DEMO_VIDEO_URL>`, `<LIVE_DEPLOYMENT_URL_OR_NOT_APPLICABLE>`, `<FINAL_COMMIT_SHA>`, `<FINAL_TAG>`, `<TEAM_NAME>`, `<TEAM_MEMBER_NAMES_AND_ROLES>`, `<NAME>`, `<ROLE>`, `<CONTRIBUTION>`

---

## 16. Verification appendix

Counts and test results recorded during hackathon submission prep (update `<FINAL_COMMIT_SHA>` at freeze).

### Word-count verification

| Section | Target | Actual | In range |
| --- | --- | --- | --- |
| ~25-word summary | 20–30 | 23 | Yes |
| ~50-word summary | 45–55 | 45 | Yes |
| ~100-word summary | 90–110 | 91 | Yes |
| ~150-word summary | 140–160 | 144 | Yes |
| Full description | 500–800 | 543 | Yes |

### Automated tests (local, this task)

| Check | Result |
| --- | --- |
| Collected | 512 |
| `pytest -q` | 511 passed, 1 skipped |
| `pytest -q tests/integration/` | 11 passed |

M5 live acceptance has **not** passed at the time of this document. Demo video and final tag are **not** claimed.
