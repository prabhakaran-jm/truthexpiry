# TruthExpiry demo preflight

The demo preflight answers one question:

**Is this machine and repository prepared to begin a TruthExpiry demo?**

It does **not** claim that Slack Real-Time Search, OpenAI extraction, or a full end-to-end product query has succeeded.

## Profiles

| Profile | When to use |
|---------|-------------|
| `live` | Primary recording: live Slack Socket Mode, live RTS, live OpenAI extraction, live lifecycle MCP |
| `backup-a` | Disclosed backup: live Slack + RTS + **fake** extractor + live MCP |
| `backup-b` | Local technical fallback before recording; no Slack/OpenAI network checks |

The selected profile is always reported explicitly. Preflight does not auto-switch profiles based on available credentials.

## Commands

```powershell
python scripts/demo_preflight.py --profile live
python scripts/demo_preflight.py --profile backup-a
python scripts/demo_preflight.py --profile backup-b
python scripts/demo_preflight.py --profile live --json
python scripts/demo_preflight.py --profile live --expected-ref v0.4.0
```

Optional flags:

| Flag | Default | Purpose |
|------|---------|---------|
| `--worker-health-base` | `http://127.0.0.1:8080` | Worker probe base (no path) |
| `--mcp-health-base` | `http://127.0.0.1:8001` | MCP health sidecar base |
| `--timeout-seconds` | `2.0` | Per-request probe timeout |
| `--repo-root` | repository root | Dataset and git checks |
| `--skip-structural` | off | Skip `app.py --check` subprocesses |
| `--expected-ref` | none | Require HEAD to match a tag or commit |

Health URLs must use `http` or `https` and must not embed credentials.

## Required environment variable names

### `live`

| Variable | Required |
|----------|----------|
| `SLACK_BOT_TOKEN` | yes |
| `SLACK_APP_TOKEN` | yes |
| `TRUTH_EXPIRY_LIFECYCLE_MCP_URL` | yes |
| `TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN` | yes |
| `TRUTH_EXPIRY_CLAIM_EXTRACTOR` | yes (`live`) |
| `OPENAI_API_KEY` | yes |
| `TRUTH_EXPIRY_USE_FAKES` | must be absent or false |

### `backup-a`

Same Slack and MCP variables as `live`, plus:

- `TRUTH_EXPIRY_CLAIM_EXTRACTOR=fake`
- `OPENAI_API_KEY` not required

### `backup-b`

No Slack, MCP, or OpenAI secrets required.

Preflight prints **variable names and states only** — never values, lengths, prefixes, or hashes.

## Safe startup order (live / backup-a)

1. Start lifecycle MCP; wait for MCP `/readyz` → HTTP 200
2. Start Slack worker with matching MCP URL and bearer token; wait for worker `/readyz` → HTTP 200
3. Verify public demo-channel evidence messages (see [`docs/MILESTONE_2.md`](../MILESTONE_2.md))
4. Run preflight for the intended profile
5. Begin recording only after `READY TO RECORD`

## Health expectations

| Service | `/healthz` | `/readyz` |
|---------|------------|-----------|
| Worker | HTTP 200 | HTTP 200 required for recording |
| Lifecycle MCP | HTTP 200 | HTTP 200 required for recording |

HTTP 503 on `/readyz` is reported as `not_ready` and fails preflight for `live` and `backup-a`.

Preflight does **not**:

- send the MCP bearer token to health endpoints
- call `/mcp` or lifecycle tools
- call Slack or OpenAI

## Dataset checks

Preflight verifies that [`lifecycle_mcp/data/lifecycle_records.json`](../lifecycle_mcp/data/lifecycle_records.json) contains demo records:

- `PROD-482` — `report_export` / `availability` / `disabled`
- `PROD-511` — `api_rate_limit` / `max_requests` / `50`

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | All required checks passed |
| `1` | Configuration / profile mismatch |
| `2` | Health or readiness failure |
| `3` | Repository, dataset, git ref, or structural failure |

When multiple categories fail, configuration failures take precedence over health, then repository/structural.

## What `READY TO RECORD` means

Infrastructure and configuration checks passed for the selected profile. You still must run the live acceptance matrix in [`live-acceptance.md`](live-acceptance.md) and confirm Slack responses during recording.
