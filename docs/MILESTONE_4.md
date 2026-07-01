# TruthExpiry Milestone 4 — Operational Hardening

Milestone 4 operationalizes TruthExpiry as two independently deployable long-running services without changing M2/M3 product semantics.

## Services

| Service | Entrypoint | Default probes |
|---------|------------|----------------|
| Slack worker | `python app.py` | `http://0.0.0.0:8080/healthz`, `/readyz` |
| Lifecycle MCP | `python -m lifecycle_mcp.server` | `http://127.0.0.1:8001/healthz`, `/readyz` |

## Configuration

Worker settings: `SlackWorkerSettings.from_env()` in `truthexpiry/config/worker.py`.

MCP settings: `LifecycleMcpServerSettings.from_env()` in `lifecycle_mcp/server_settings.py`.

- **Parse** (`from_env`) — types and defaults only; no runtime credentials required.
- **Runtime** (`validate_runtime`) — credentials and live-adapter requirements for normal startup.
- **Structural check** — `python app.py --check` or `python -m lifecycle_mcp.server --check` parses configuration only.

## MCP availability behavior

- **Invalid configuration** (malformed MCP URL, missing URL/token in live mode) fails worker startup before Socket Mode is constructed.
- **Temporary MCP outage** does **not** terminate the worker. The process stays alive, `/healthz` remains 200, and `/readyz` returns 503 until MCP recovers.
- One immediate MCP readiness probe runs during worker startup, then a background monitor polls MCP `GET /readyz` continuously with bounded internal backoff (0.5s initial interval, 2s cap). Per-request timeout uses `TRUTH_EXPIRY_MCP_CLIENT_TIMEOUT_SECONDS`. There is **no total startup deadline**; temporary outage never terminates a correctly configured worker.
- Recovery flips readiness to 200 without restarting the worker. Later outages flip readiness back to 503.
- Readiness probes use HTTP only — no OpenAI calls and no lifecycle tool invocations.

## Health responses

Probe JSON never includes tokens, queries, evidence bodies, or Slack content. See `truthexpiry/ops/health.py`.

MCP `/readyz` on the health sidecar is **unauthenticated** and must be reachable only on a private network. Worker MCP transport uses bearer auth on `/mcp` when auth is enabled.

For production, set `TRUTH_EXPIRY_LIFECYCLE_MCP_HEALTH_URL` when the health port or host differs from the derived default.

## Shutdown

On SIGTERM/SIGINT the worker sets `draining=yes` (immediate `/readyz` 503), stops MCP and Socket Mode monitors, closes Socket Mode intake, rejects new handler work, drains in-flight requests, then stops health and metrics servers.

## Event deduplication

Optional `TRUTH_EXPIRY_DEDUP_EVENT_IDS=1` enables bounded in-memory Slack `event_id` deduplication (disabled by default).

## Containers

Production images are multi-stage wheel installs (non-editable). Runtime user `truthexpiry` (uid 10001).

## Local verification

```powershell
python app.py --check
python -m lifecycle_mcp.server --check
pytest -q tests/unit/test_health.py tests/unit/test_shutdown.py tests/unit/test_mcp_health.py
pytest -q tests/integration/test_deployment_smoke.py
docker build -f Dockerfile -t truthexpiry-worker:local .
docker build -f Dockerfile.lifecycle-mcp -t truthexpiry-lifecycle-mcp:local .
```

## Manual acceptance checklist

1. Worker `--check` succeeds with no Slack/OpenAI/MCP secrets in environment.
2. MCP `--check` succeeds with auth disabled or valid token configured.
3. Worker `/healthz` returns 200 while process is up.
4. Worker `/readyz` returns 503 until Socket Mode connects and MCP is available (live), or all checks pass (fake).
5. MCP `/readyz` returns 200 after dataset load and tool registration.
6. Bearer token required on MCP `/mcp` when auth enabled.
7. Temporary MCP outage keeps worker alive with `/readyz` 503; recovery restores readiness without restart.
8. SIGTERM sets draining, closes Socket Mode intake, then drains in-flight handler work.
9. Logs exclude query text and tokens (caplog privacy tests).
10. Container images build from wheels and run as non-root user `truthexpiry` (uid 10001).
