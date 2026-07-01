# TruthExpiry demo operator guide

Central guide for preparing, recording, and accepting the hackathon demo. All modes are **explicit** — never auto-switch profiles.

**Related:** [preflight](preflight.md) · [recording script](recording-script.md) · [shot list](shot-list.md) · [live acceptance](live-acceptance.md) · [troubleshooting](troubleshooting.md) · [architecture source](../architecture/truthexpiry-architecture.mmd) · [technical proof](../submission/technical-proof.md) · [submission copy](../submission/submission-copy.md)

---

## Purpose

This guide coordinates:

| Step | Document |
| --- | --- |
| Readiness checks | [preflight.md](preflight.md) |
| Slack channel and evidence setup | This guide — [Dedicated Slack demo channel](#dedicated-slack-demo-channel-setup) |
| Timed narration and queries | [recording-script.md](recording-script.md) |
| Screenshot and media capture | [shot-list.md](shot-list.md) |
| Sign-off after live run | [live-acceptance.md](live-acceptance.md) |
| Recovery during prep | [troubleshooting.md](troubleshooting.md) |

---

## Demo profiles

### Primary — `live`

| Component | Mode |
| --- | --- |
| Slack Socket Mode | Live |
| `assistant.search.context` | Live |
| OpenAI claim extraction | Live (`TRUTH_EXPIRY_CLAIM_EXTRACTOR=live`) |
| Lifecycle MCP | Live |
| Validity labeler | Deterministic (always) |

Use for the **primary hackathon video** unless a documented backup is required.

### Backup A — `backup-a`

| Component | Mode |
| --- | --- |
| Slack + RTS + MCP | Live |
| Claim extraction | **Fake** adapter |

**Must be disclosed** verbally and on screen before showing product output. See [recording-script.md — Backup-mode disclosure](recording-script.md#backup-mode-disclosure).

### Backup B — `backup-b`

Repository, preflight, and test proof only. **Not** a live Slack product demo. Do not present pytest or preflight JSON as if it were a live Slack interaction.

Profiles are **never** auto-switched. Set environment and preflight profile explicitly.

---

## Recording baseline

Complete before recording and store with the final video metadata.

| Field | Value |
| --- | --- |
| Branch | `feat/m5-hackathon-submission` (or `<RECORDING_BRANCH>`) |
| Commit | `<RECORDING_COMMIT_SHA>` |
| Tag | `<RECORDING_TAG>` (if any; `v1.0.0` does **not** exist yet) |
| Profile | `live` / `backup-a` / `backup-b` |
| Date | `<RECORDING_DATE>` |
| Slack workspace | `<SLACK_WORKSPACE_NAME>` |
| Public demo channel | `<PUBLIC_DEMO_CHANNEL_NAME>` |
| Recorder | `<RECORDER_NAME>` |
| Video duration limit | `<PLATFORM_MAX_DURATION>` (assumed hard max **3:00**; **target 2:50** until platform confirms) |
| Final video URL | `<DEMO_VIDEO_URL>` |

---

<a id="dedicated-slack-demo-channel-setup"></a>

## Dedicated Slack demo channel setup

Use a **dedicated public channel** with controlled synthetic evidence. Confirm the invoking user has joined the channel and the app has `search:read.public`.

### Required public messages

Post these (or equivalent wording that preserves entity, polarity, and PROD-* references):

| # | Message text | Lifecycle reference |
| --- | --- | --- |
| 1 | `Report export on the Starter plan is enabled. Tracked in PROD-481.` | PROD-481 (superseded) |
| 2 | `Report export on the Starter plan is disabled. Tracked in PROD-482.` | PROD-482 (current) |
| 3 | `Starter API rate limit is 100 requests. Tracked in PROD-510.` | PROD-510 (superseded) |
| 4 | `Starter API rate limit is 50 requests. Tracked in PROD-511.` | PROD-511 (current) |

Messages **1–2** are documented in [MILESTONE_2.md](../MILESTONE_2.md). Messages **3–4** align with [MILESTONE_3.md](../MILESTONE_3.md) acceptance queries and lifecycle records; add them before recording Scene 4.

### Private-channel decoy (acceptance test only)

For live-acceptance row 9 ([live-acceptance.md](live-acceptance.md)):

1. Post different content in a **private channel** (for example a unique decoy phrase).
2. Confirm RTS does **not** return that content for public demo queries.
3. **Do not** show the private channel in the final recording.

### Do not

- Edit `lifecycle_mcp/data/lifecycle_records.json` for a desired label.
- Paste edited Slack output into the recording.
- Use real customer or private workspace content.

---

## Startup order

Run from repository root with secrets in `.env` (never display on screen).

| Step | Action | Pass criterion |
| --- | --- | --- |
| 1 | Start lifecycle MCP: `python -m lifecycle_mcp.server` | Process running |
| 2 | MCP liveness | `GET http://127.0.0.1:8001/healthz` → HTTP 200 |
| 3 | MCP readiness | `GET http://127.0.0.1:8001/readyz` → HTTP 200 |
| 4 | Start worker: `python app.py` | Socket Mode connecting |
| 5 | Worker liveness | `GET http://127.0.0.1:8080/healthz` → HTTP 200 |
| 6 | Worker readiness | `GET http://127.0.0.1:8080/readyz` → HTTP 200 |
| 7 | Demo preflight | `python scripts/demo_preflight.py --profile live` → exit 0, `READY TO RECORD` |
| 8 | Slack app | Connected; fresh thread ready in public demo channel |
| 9 | Screen hygiene | Close unrelated windows; disable notifications; hide `.env` |
| 10 | Start recording | After steps 1–9 pass |

Adjust health host/ports if overridden via environment variables.

---

## Reset procedure

Between retakes or scenes:

1. **Restart services** if health/readiness failed or MCP auth drifted.
2. **Clear terminal** scrollback or open a clean terminal (no `env`, `printenv`, or secret exports in history).
3. **Confirm profile** — `TRUTH_EXPIRY_CLAIM_EXTRACTOR=live` and `TRUTH_EXPIRY_USE_FAKES` unset for primary path.
4. **Duplicate events** — send a **new** app mention or DM if `TRUTH_EXPIRY_DEDUP_EVENT_IDS=1` suppressed a repeat.
5. **Do not alter** lifecycle JSON.
6. **Re-run preflight** for the intended profile.
7. **Fresh Slack thread** or new top-level message to obtain a new `action_token`.

<a id="retake-rules"></a>

## Retake rules

**Stop and retake immediately** when:

| Trigger | Why |
| --- | --- |
| Wrong validity label | Misrepresents product |
| Private channel or DM evidence visible | Privacy violation |
| Token, `.env`, or bearer secret on screen | Security incident |
| Profile mismatch (e.g. fake extractor without disclosure) | Truthfulness violation |
| Pasted or edited Slack output | Not live interaction |
| Response truncated so label or PROD-* ID is unreadable | Unverifiable demo |
| Cursor or overlay obscures result | Judge cannot verify |
| Notification reveals personal data | Privacy |
| Health JSON contradicts narration | Operational falsehood |

Brief OpenAI latency (under [max wait](recording-script.md#latency-handling)) with honest narration is acceptable. Do **not** splice output from a different query, take, or profile.

---

## Links

| Resource | Path |
| --- | --- |
| Preflight | [preflight.md](preflight.md) |
| Recording script | [recording-script.md](recording-script.md) |
| Shot list | [shot-list.md](shot-list.md) |
| Live acceptance | [live-acceptance.md](live-acceptance.md) |
| Troubleshooting | [troubleshooting.md](troubleshooting.md) |
| Architecture | [../architecture/truthexpiry-architecture.mmd](../architecture/truthexpiry-architecture.mmd) |
| Technical proof | [../submission/technical-proof.md](../submission/technical-proof.md) |
| Submission copy | [../submission/submission-copy.md](../submission/submission-copy.md) |
| Asset export | [../assets/README.md](../assets/README.md) |
