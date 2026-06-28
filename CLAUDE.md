# Claude Code — TruthExpiry

Read these files **before** making changes:

1. [`AGENTS.md`](AGENTS.md) — architecture, milestones, ports, retention policy, commands
2. [`REVIEW.md`](REVIEW.md) — pre-merge checklist (RTS compliance, no Slack retention, no LLM validity, secrets)

## Hard rules (summary)

- M0 is **offline only**: fake adapters, no live RTS/MCP/LLM in tests or default paths.
- **Deterministic labeler** assigns `CURRENT` / `SUPERSEDED` / `CONFLICTING` / `UNVERIFIED`; the LLM extracts claims only.
- **No persistence** of Slack-derived message text, RTS results, or LLM history across requests.
- **Public channels only** for MVP search; Slack MCP disabled.
- Listeners are a **thin boundary** — delegate to `TruthExpiryPipeline`, no business logic.
- Do not commit `.cursor/`, `.claude/`, `.env`, or credentials.

When in doubt, follow `AGENTS.md` and verify with the commands listed there.
