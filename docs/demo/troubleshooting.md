# TruthExpiry demo troubleshooting

Use this guide during demo setup and recording. Do not weaken grounding, bypass bearer authentication, edit lifecycle records for a desired label, or surface private Slack content.

## Worker `/readyz` is 503 — Socket Mode connecting

**Symptoms:** Worker `/healthz` is 200 but `/readyz` is 503; readiness JSON shows `socket_mode: connecting`.

**Actions:**

1. Wait for Socket Mode to connect (monitor polls every ~2s).
2. Confirm `SLACK_APP_TOKEN` and `SLACK_BOT_TOKEN` are set (preflight checks names only).
3. Re-run preflight after connection stabilizes.

## Worker `/readyz` is 503 — MCP unavailable

**Symptoms:** `lifecycle_mcp: unavailable` in worker readiness JSON.

**Actions:**

1. Confirm lifecycle MCP is running and MCP `/readyz` returns 200.
2. Verify `TRUTH_EXPIRY_LIFECYCLE_MCP_URL` and bearer token match MCP server config.
3. Check worker `TRUTH_EXPIRY_LIFECYCLE_MCP_HEALTH_URL` if health is not on the default derived port.
4. Review MCP logs for dataset or tool-registration failures.

## MCP auth mismatch

**Symptoms:** Worker readiness or MCP transport failures; MCP logs show auth errors.

**Actions:**

1. Rotate to a matching `TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN` on **both** processes.
2. Do not place bearer tokens in health URLs.
3. For local dev only, `TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_DISABLED=1` on MCP (not for primary recording).

## OpenAI unavailable

**Symptoms:** Generic extraction-unavailable Slack response in live mode.

**Actions:**

1. Confirm `OPENAI_API_KEY` is set and `TRUTH_EXPIRY_CLAIM_EXTRACTOR=live`.
2. Confirm `TRUTH_EXPIRY_USE_FAKES` is unset.
3. For backup recording, switch to `backup-a` profile and **disclose fake extraction on screen**.

## Slack action token stale

**Symptoms:** RTS errors; no search results; adapter rejects blank token.

**Actions:**

1. Send a **new** app mention or DM to obtain a fresh request-scoped `action_token`.
2. Query immediately in the same event turn — tokens are not cached or reused.

## Unexpected RTS evidence ordering

**Symptoms:** Evidence order differs from scripted messages.

**Actions:**

1. Use a dedicated public demo channel with only the documented evidence messages.
2. Do not rely on permalink order; validity comes from lifecycle evidence, not message recency.
3. Re-post controlled evidence messages if the channel drifted.

## Wrong extractor or profile selected

**Symptoms:** Labels match tests but extraction behavior looks deterministic/heuristic.

**Actions:**

1. Run `python scripts/demo_preflight.py --profile live --json` and confirm profile and `claim_extractor` checks.
2. For disclosed backup, use `--profile backup-a` and state fake extraction in narration.

## Duplicate event suppression

**Symptoms:** Second identical query in quick succession produces no response.

**Actions:**

1. Check `TRUTH_EXPIRY_DEDUP_EVENT_IDS` — disabled by default.
2. If enabled, use a new Slack event or wait for TTL/eviction.

## Port collision

**Symptoms:** Health probes fail; services fail to bind.

**Actions:**

1. Default ports: worker health `8080`, metrics `9090`, MCP `8000`, MCP health `8001`.
2. Override with configuration env vars and matching `--worker-health-base` / `--mcp-health-base`.

## Terminal or recording privacy incident

**Symptoms:** Token, `.env`, or private Slack content visible on screen.

**Actions:**

1. **Stop recording immediately.**
2. Rotate any exposed credentials.
3. Retake from a clean terminal session without printing env values.

## Network outage during recording

**Actions:**

1. Pause narration; do not paste canned Slack output.
2. Restore MCP and worker health; re-run preflight.
3. Retake the affected scene if live output was not captured.

## When to retake vs continue

| Retake | Continue |
|--------|----------|
| Wrong validity label | Brief OpenAI latency with honest narration |
| Private content appeared | Socket Mode connecting → connected |
| Token visible on screen | Single RTS hit order difference |
| Used wrong profile without disclosure | |

## Backup paths

| Level | Path | Disclosure required |
|-------|------|---------------------|
| Primary | `live` profile | None |
| Backup A | `backup-a` profile | Fake extractor on screen |
| Backup B | pytest / fixture proof | Not a live Slack demo |
