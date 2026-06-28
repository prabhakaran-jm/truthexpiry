# Scaffold inspection report

Generated: 2026-06-28  
Branch: `feat/m0-foundation`

## Generation method

| Step | Result |
|------|--------|
| Primary: `slack version` then `slack create agent scaffold` | **Not available** — `slack` on PATH resolves to `Slack.exe` (desktop app), not the Slack developer CLI |
| Fallback: `slack create scaffold -t slack-samples/bolt-python-starter-agent --subdir pydantic-ai` | **Not available** — same desktop binary |
| **Used:** git clone fallback | `git clone --depth 1 https://github.com/slack-samples/bolt-python-starter-agent.git` → copy `pydantic-ai/` → `scaffold/` |

Equivalent to selecting **Starter Agent → Bolt for Python → Pydantic AI** from the official template repo.

## Scaffold location

```
scaffold/
```

34 files under `scaffold/` including `.env.sample`, `app.py`, `manifest.json`, `agent/`, `listeners/`, `tests/`, `thread_context/`.

## Dependency versions (from `scaffold/pyproject.toml` and `scaffold/requirements.txt`)

| Package | Version |
|---------|---------|
| Python | `>=3.10` |
| slack-sdk | 3.42.0 |
| slack-bolt | 1.28.0 |
| slack-cli-hooks | 0.3.0 |
| pydantic-ai | 1.107.0 (`[openai]` in pyproject; `[openai,anthropic]` in requirements.txt) |
| python-dotenv | 1.2.2 |
| pytest | 9.1.1 |
| ruff | 0.15.20 |

## Layout vs plan assumptions

| Item | Actual | Plan note |
|------|--------|-----------|
| Project name in pyproject | `bolt-python-support-agent-pydantic` | Will rename to `truthexpiry` at merge |
| Root pyproject | Per-variant only (no monorepo root pyproject) | `.github/` copied from monorepo separately at merge |
| Env template | `.env.sample` (not `.env.example`) | As upstream |
| Conversation store | `thread_context/store.py` present | Will remove/replace in M0 |
| Slack MCP | Enabled in `agent/agent.py` when user token present | Will disable in M0 |
| Manifest MCP flag | `"is_mcp_enabled": true` | Will set false in M0 |
| User OAuth scopes | Extensive `search:read.*` user scopes | Will remove in M0; add `search:read.public` bot scope |
| Bot events | Includes `message.channels`, `message.groups` | Will trim to MVP entry points at merge |

## Manifest bot scopes (upstream)

```
app_mentions:read, channels:history, chat:write, groups:history,
im:history, im:read, im:write, reactions:write, reactions:read,
users:read, assistant:write
```

No `search:read.public` on bot scope yet (required for M2 bot-token RTS).

## Entry points

- `app.py` — Socket Mode (`SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`)
- `app.py` — Socket Mode entrypoint (M0)

## Merge status

Scaffold files were merged into the repository root during Milestone 0 Todo 2. The temporary `scaffold/` directory was deleted after merge; the root tree is the canonical application layout.
