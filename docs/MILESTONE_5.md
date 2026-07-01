# TruthExpiry Milestone 5 — Hackathon demo proof and submission

Milestone 5 turns the technically complete TruthExpiry stack into a judge-ready hackathon submission without changing M0–M4 product semantics.

## Objective

Deliver a reproducible demo, evidence-backed technical story, polished repository entry points, and submission assets while preserving the core invariant:

**The LLM extracts structured claims only. Deterministic code assigns validity.**

## In scope (M5)

- Safe demo preflight tooling and documentation
- Final live-acceptance matrix template
- Screenshot capture checklist (planned)
- Final repository polish and release tag (planned)

## Out of scope

- Product architecture redesign
- Changes to Slack RTS semantics, extraction model, labeler, lifecycle dataset, or MCP tool schema
- Invented hackathon rules or sponsor claims

## Commit 1

Implemented:

- [`scripts/demo_preflight.py`](../scripts/demo_preflight.py) — read-only demo readiness command
- [`truthexpiry/demo/preflight.py`](../truthexpiry/demo/preflight.py) — core preflight logic
- [`docs/demo/preflight.md`](demo/preflight.md) — operator guide
- [`docs/demo/live-acceptance.md`](demo/live-acceptance.md) — final acceptance matrix template
- [`docs/demo/troubleshooting.md`](demo/troubleshooting.md) — demo recovery guide
- Unit tests in [`tests/unit/test_demo_preflight.py`](../tests/unit/test_demo_preflight.py)

## Commit 2

Implemented:

- [`docs/architecture/truthexpiry-architecture.mmd`](architecture/truthexpiry-architecture.mmd) — judge-facing Mermaid architecture source
- [`docs/assets/README.md`](assets/README.md) — export commands and media privacy rules
- [`docs/submission/technical-proof.md`](submission/technical-proof.md) — verification-oriented technical proof

## Commit 3

Implemented:

- [`README.md`](../README.md) — judge-facing repository entry point

## Commit 4

Implemented:

- [`docs/submission/submission-copy.md`](submission/submission-copy.md) — hackathon submission copy package

## Commit 5 (this slice)

Implemented:

- [`docs/demo/README.md`](demo/README.md) — consolidated demo operator guide
- [`docs/demo/recording-script.md`](demo/recording-script.md) — timed recording script (2:50 target, 3:00 max)
- [`docs/demo/shot-list.md`](demo/shot-list.md) — screenshot and asset capture checklist

## Truthful demo modes

| Profile | Purpose |
|---------|---------|
| `live` | Primary recording path: live Slack, live RTS, live OpenAI, live MCP |
| `backup-a` | Disclosed backup: live Slack + RTS + **fake** extractor + live MCP |
| `backup-b` | Local technical fallback: repository/dataset/structural checks only |

Preflight **does not** verify that a live Slack query succeeded. `READY TO RECORD` means infrastructure and configuration readiness only.

## Frozen product boundaries

Do not modify in M5 without explicit justification:

- `adapters/slack_rts/`, `adapters/llm/`
- `listeners/events/`, `listeners/truthexpiry_handler.py`
- `truthexpiry/services/labeler.py`, `query_grounding.py`, `query_claim_fallback.py`, `pipeline.py`
- `lifecycle_mcp/data/lifecycle_records.json`
- OpenAI model (`openai:gpt-4.1-mini`), 20s timeout, `retries=0`
- Public-channel-only RTS, one RTS call per invocation

## Remaining planned work

- Capture architecture exports and Slack screenshots per [`docs/demo/shot-list.md`](demo/shot-list.md)
- Record and upload demo video
- Final live acceptance sign-off
- Insert final links and badges in README / submission copy
- Independent M5 review
- Final release metadata and tag (e.g. `v1.0.0`)

See the M5 planning document in `.cursor/plans/` for the full sequence.
