# TruthExpiry

TruthExpiry prevents Slack agents from repeating stale information. A user asks a question in Slack. The app retrieves candidate claims from **public channels**, obtains authoritative lifecycle evidence, and uses deterministic rules to label each claim `CURRENT`, `SUPERSEDED`, `CONFLICTING`, or `UNVERIFIED`.

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

For architecture, milestones, and agent rules, see [AGENTS.md](AGENTS.md) and [REVIEW.md](REVIEW.md).

## Development

`pyproject.toml` is the canonical dependency declaration. Use an editable install so imports resolve to this worktree instead of a stale site-packages copy.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Copy `.env.sample` to `.env` and configure Slack tokens before running locally with `python app.py` or `slack run`.

Milestone 0 entrypoint: `python app.py` (Socket Mode). OAuth HTTP mode is deferred.
