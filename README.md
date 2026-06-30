# TruthExpiry

TruthExpiry prevents Slack agents from repeating stale information. A user asks a question in Slack. The app retrieves candidate claims from **public channels**, obtains authoritative lifecycle evidence, and uses deterministic rules to label each claim `CURRENT`, `SUPERSEDED`, `CONFLICTING`, or `UNVERIFIED`.

**Milestone 1** adds a local Streamable HTTP lifecycle MCP server with synthetic Jira-like evidence. Validity labels are assigned only by deterministic domain code in `truthexpiry/services/labeler.py` — the MCP server returns evidence records only.

## MVP scope

The initial demonstration uses:

- **Socket Mode** with a bot token and event-provided `action_token`
- **Public Slack channels only** (for example `#product-help`, `#product-planning`, `#product-updates`)
- No private-channel, DM, or MPDM search in the MVP
- No user-token OAuth until the public-channel flow is complete

Private search is not supported in the MVP UI or manifest.

## Stack

Built on the official [Slack Starter Agent](https://github.com/slack-samples/bolt-python-starter-agent) template (**Bolt for Python** + **Pydantic AI**).

See [docs/SCAFFOLD_INSPECTION.md](docs/SCAFFOLD_INSPECTION.md) for the generated scaffold layout and dependency versions.

For architecture, milestones, and agent rules, see [AGENTS.md](AGENTS.md), [REVIEW.md](REVIEW.md), [docs/MILESTONE_1.md](docs/MILESTONE_1.md), [docs/MILESTONE_2.md](docs/MILESTONE_2.md), [docs/MILESTONE_3.md](docs/MILESTONE_3.md), and [docs/MILESTONE_4.md](docs/MILESTONE_4.md).

## Development

`pyproject.toml` is the canonical dependency declaration. Use an editable install so imports resolve to this worktree instead of a stale site-packages copy.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Copy `.env.sample` to `.env` and configure Slack tokens before running locally with `python app.py` or `slack run`.

### All-fake mode (default local)

```powershell
$env:TRUTH_EXPIRY_USE_FAKES = "1"
python app.py
```

### Real lifecycle MCP + live Slack RTS (Milestone 2)

```powershell
# Terminal 1 — start server
python -m lifecycle_mcp.server

# Terminal 2 — Slack app (unset TRUTH_EXPIRY_USE_FAKES)
$env:TRUTH_EXPIRY_LIFECYCLE_MCP_URL = "http://127.0.0.1:8000/mcp"
python app.py
```

See [docs/MILESTONE_2.md](docs/MILESTONE_2.md) for eligibility, manual acceptance, and privacy rules.

### Live claim extraction (Milestone 3)

```powershell
# Terminal 1 — lifecycle MCP
python -m lifecycle_mcp.server

# Terminal 2 — Slack app (unset TRUTH_EXPIRY_USE_FAKES)
$env:TRUTH_EXPIRY_LIFECYCLE_MCP_URL = "http://127.0.0.1:8000/mcp"
$env:TRUTH_EXPIRY_CLAIM_EXTRACTOR = "live"
$env:OPENAI_API_KEY = "sk-..."
python app.py
```

See [docs/MILESTONE_3.md](docs/MILESTONE_3.md) for structured-output rules, evidence grounding, and manual acceptance.

### Operational hardening (Milestone 4)

Two independently deployable processes: the **Slack Socket Mode worker** (`app.py`) and the **lifecycle MCP HTTP server** (`python -m lifecycle_mcp.server`). Configuration is typed and validated at startup; health probes expose `/healthz` (liveness) and `/readyz` (readiness) without leaking secrets.

**Credential-free structural check** (parse config only — no Slack, OpenAI, or MCP secrets required):

```powershell
python app.py --check
python -m lifecycle_mcp.server --check
```

**Health probes (defaults):**

| Service | Liveness | Readiness |
|---------|----------|-----------|
| Slack worker | `http://127.0.0.1:8080/healthz` | `http://127.0.0.1:8080/readyz` |
| Lifecycle MCP | `http://127.0.0.1:8001/healthz` | `http://127.0.0.1:8001/readyz` |

**Container images (local):**

```powershell
docker build -f Dockerfile -t truthexpiry-worker:local .
docker build -f Dockerfile.lifecycle-mcp -t truthexpiry-lifecycle-mcp:local .
docker run --rm truthexpiry-worker:local python app.py --check
```

Optional local wiring: `docker compose up` (see `docker-compose.yml`). For deployment steps, rollback triggers, and secret rotation, see [docs/runbooks/](docs/runbooks/).

See [docs/MILESTONE_4.md](docs/MILESTONE_4.md) for the full M4 contract, environment variables, and acceptance checklist.

Milestone 0 entrypoint: `python app.py` (Socket Mode). OAuth HTTP mode is deferred.
