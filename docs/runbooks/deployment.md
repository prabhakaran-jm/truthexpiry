# Deployment runbook

## Prerequisites

- Two containers or processes: Slack worker + lifecycle MCP
- Private network path from worker to MCP URL
- Secrets injected via environment (never baked into images)

## Deploy sequence

1. Deploy lifecycle MCP first; wait for `/readyz` on the health port (default `8001`).
2. Configure worker `TRUTH_EXPIRY_LIFECYCLE_MCP_URL` and `TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN`.
3. Deploy worker; confirm `/healthz` then `/readyz` on port `8080`.
4. Run `python app.py --check` in CI or init container before rolling traffic.

## Smoke tests

```powershell
curl -f http://127.0.0.1:8001/healthz
curl -f http://127.0.0.1:8001/readyz
curl -f http://127.0.0.1:8080/healthz
```

## Rollback triggers

- Worker `/readyz` stays `503` beyond MCP readiness timeout
- MCP dataset fails to load at startup
- Elevated `requests_total{outcome=failure}` without upstream incident

## Rollback

1. Scale worker to zero or revert to previous image tag.
2. MCP can remain running if dataset contract unchanged.
3. Verify fake-mode worker starts in staging before re-attempting live rollout.
