# TruthExpiry Milestone 2 — Live Slack RTS

Milestone 2 replaces the fake RTS adapter with live **public-channel** Slack Real-Time Search while keeping fake deterministic claim extraction and the Milestone 1 lifecycle MCP.

## Architecture

```text
Slack app_mention or message.im event
    → listener (forwards action_token)
    → TruthExpiryPipeline
    → SlackRtsAdapter
    → assistant.search.context (one call per invocation)
    → EphemeralRtsHits
    → rts_sanitizer (extract_ticket_ref from content)
    → FakeClaimExtractionPort
    → LifecycleMcpAdapter
    → deterministic labeler
    → Slack response with source permalinks
```

The Slack adapter retrieves evidence only. It never assigns `CURRENT`, `SUPERSEDED`, `CONFLICTING`, or `UNVERIFIED`.

## One Slack API call per request

The pipeline does **not** call `assistant.search.info` during request processing.

Each supported invocation makes at most one `assistant.search.context` call with `disable_semantic_search=False`. Slack performs semantic search when available and keyword fallback otherwise.

No pagination, automatic retries, or request-time capability lookup.

## SDK workaround

Slack documents `WebClient.assistant_search_context`, but `slack-sdk==3.42.0` does not yet ship a generated helper. The adapter uses one predictable path:

```python
client.api_call(
    api_method="assistant.search.context",
    http_verb="POST",
    json=payload,
)
```

## Action-token lifecycle

- Listeners forward the request-scoped RTS `action_token` from the Slack event (`action_token` or `assistant_thread.action_token`) without logging or validating it.
- `FakeRtsPort` ignores the token.
- `SlackRtsAdapter` rejects missing or blank tokens before any Slack call.
- Tokens are request-scoped only: never logged, cached, persisted, or included in repr/exceptions.
- Use the token immediately during the triggering event request.

## Privacy

Request-scoped `EphemeralRtsHit` objects may contain Slack message text during a single handler invocation. After the Slack response is rendered, all Slack-derived content is discarded.

Allowed logs: method name, safe outcome category, result count, duration, safe Slack error code.

Never log: user query, message text, permalinks, display names, action tokens, bot tokens, event payloads, or complete Slack responses.

## Composition matrix

```text
TRUTH_EXPIRY_USE_FAKES=1
    → FakeRtsPort + FakeClaimExtractionPort + FakeLifecycleEvidenceAdapter

TRUTH_EXPIRY_USE_FAKES unset + app.client + TRUTH_EXPIRY_LIFECYCLE_MCP_URL
    → SlackRtsAdapter + FakeClaimExtractionPort + LifecycleMcpAdapter

TRUTH_EXPIRY_USE_FAKES unset + missing client or MCP URL
    → LiveAdaptersUnavailableError at composition time
```

`app.py` composes the pipeline once at startup with `build_pipeline(slack_client=app.client)`.

## Slack RTS eligibility

Slack RTS is available for **internal apps** and **directory-published apps**. An ordinary **unlisted distributed app** is not an eligible deployment model.

This project targets an internal development workspace.

## Scopes and reinstall

- Bot scope: `search:read.public` only (already in `manifest.json`).
- Reinstall the app after scope changes.
- Do not add private, IM, MPIM, file, or user search scopes for M2.

## Local startup (two processes)

```powershell
# Terminal 1 — lifecycle MCP
python -m lifecycle_mcp.server

# Terminal 2 — Slack app (unset TRUTH_EXPIRY_USE_FAKES)
$env:TRUTH_EXPIRY_LIFECYCLE_MCP_URL = "http://127.0.0.1:8000/mcp"
python app.py
```

## Manual acceptance

**Prerequisites**

- Eligible internal development app
- `search:read.public` installed and app reinstalled after scope changes
- Invoking user has joined the synthetic public demo channel
- Lifecycle MCP running at `TRUTH_EXPIRY_LIFECYCLE_MCP_URL`
- `TRUTH_EXPIRY_USE_FAKES` unset
- `action_token` used immediately during the event request

**Synthetic public-channel messages**

1. `Report export on the Starter plan is enabled. Tracked in PROD-481.`
2. `Report export on the Starter plan is disabled. Tracked in PROD-482.`
3. (Optional) Different content in a private channel — must not appear in results

**Demo queries**

| Query | Expected status |
|-------|-----------------|
| `Is report export available on the starter plan?` | `SUPERSEDED` (PROD-482 disabled supersedes PROD-481 enabled) |
| `Is report export disabled on the starter plan?` | `CURRENT` (PROD-482) |

Verify: one RTS call, public permalinks in response, lifecycle record IDs cited, no private content surfaced, no local persistence of message bodies.

## Exclusions (M2)

Private/DM/MPDM/file/user/channel search; OAuth; user tokens; Slack MCP; `conversations.history` / `conversations.replies`; pagination; per-request `assistant.search.info`; retries; live LLM extraction; caches; databases; deployment; lifecycle MCP changes; labeler changes.
