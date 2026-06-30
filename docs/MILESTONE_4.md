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

## Health responses

Probe JSON never includes tokens, queries, evidence bodies, or Slack content. See `truthexpiry/ops/health.py`.

## Local verification

```powershell
python app.py --check
python -m lifecycle_mcp.server --check
pytest -q tests/unit/test_health.py tests/unit/test_shutdown.py
docker build -f Dockerfile -t truthexpiry-worker:local .
docker build -f Dockerfile.lifecycle-mcp -t truthexpiry-lifecycle-mcp:local .
```

## Manual acceptance checklist

1. Worker `--check` succeeds with no Slack/OpenAI/MCP secrets in environment.
2. MCP `--check` succeeds with auth disabled or valid token configured.
3. Worker `/healthz` returns 200 while process is up.
4. Worker `/readyz` returns 503 until Socket Mode connects (live) or all checks pass (fake).
5. MCP `/readyz` returns 200 after dataset load.
6. Bearer token required on MCP `/mcp` when auth enabled.
7. SIGTERM drains in-flight handler work up to `TRUTH_EXPIRY_SHUTDOWN_DRAIN_SECONDS`.
8. Logs exclude query text and tokens (caplog privacy tests).
9. Container images build and run as non-root user `truthexpiry` (uid 10001).
