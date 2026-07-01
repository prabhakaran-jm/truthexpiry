# TruthExpiry timed demo recording script

Executable script for the **primary `live` profile** hackathon video.

**Assumed hard maximum: 3:00.** Confirm against the hackathon platform before recording. **Target timeline: 2:50** — leaves ~10 seconds of margin for Slack rendering, cursor movement, transitions, narration pauses, and platform rounding. Do not plan to end at 3:00.

**Operator guide:** [README.md](README.md) · **Capture checklist:** [shot-list.md](shot-list.md)

---

## Timeline overview

| Segment | Time | Duration |
| --- | --- | --- |
| Hook | 0:00–0:15 | 0:15 |
| Architecture promise | 0:15–0:32 | 0:17 |
| Scene 1 — SUPERSEDED | 0:32–1:05 | 0:33 |
| Scene 2 — CURRENT | 1:05–1:28 | 0:23 |
| Scene 3 — safe guidance | 1:28–1:45 | 0:17 |
| Scene 4 — numeric SUPERSEDED | 1:45–2:08 | 0:23 |
| Scene 5 — record flip | 2:08–2:28 | 0:20 |
| Close | 2:28–2:50 | 0:22 |
| **Total (target)** | | **2:50** |

**Dropped from primary video:** MCP outage recovery (Option B). Capture that as an optional supplementary clip per [shot-list.md](shot-list.md) — do not risk the 2:50 budget on live process restarts.

---

## 0:00–0:15 — Hook

| Field | Detail |
| --- | --- |
| **Screen** | Title card, cropped Slack window, or README/architecture opening — **no secret-bearing terminal** |
| **Action** | Hold static or slow pan; no typing yet |
| **Narration** | “The most similar Slack message may be the statement that is already obsolete. **Similarity is not validity.**” |
| **Cursor** | Off-screen or lower corner |
| **Zoom** | N/A |
| **Max wait** | 15 s (narration must finish within segment) |
| **Retake if** | Token, `.env`, or unrelated workspace content visible |
| **Fallback** | Shorten to one sentence if over time; do not skip the tagline |

---

## 0:15–0:32 — Architecture promise

| Field | Detail |
| --- | --- |
| **Screen** | Simplified Mermaid from [README](../../README.md) or full [architecture source](../architecture/truthexpiry-architecture.mmd) — highlight **Probabilistic extraction** vs **Deterministic validation** |
| **Action** | Point to OpenAI box vs labeler/MCP boxes (mouse highlight only) |
| **Narration** | “TruthExpiry searches **public Slack evidence**. OpenAI extracts **zero or one** structured claim. Lifecycle MCP returns lifecycle records. **Deterministic code** assigns CURRENT, SUPERSEDED, CONFLICTING, or UNVERIFIED. The **model never assigns validity**.” |
| **Cursor** | Trace flow left-to-right |
| **Zoom** | 100–125% on diagram |
| **Max wait** | 17 s |
| **Retake if** | Diagram implies the LLM chooses validity labels |
| **Fallback** | Use README architecture block if export not yet captured |

---

<a id="scene-1-supereded"></a>

## 0:32–1:05 — Scene 1: SUPERSEDED

| Field | Detail |
| --- | --- |
| **Screen** | Public demo channel; TruthExpiry thread with **Block Kit** verdict |
| **Exact query** | `Is report export available on the Starter plan?` |
| **Expected result** | Header **Superseded**; stated value `enabled`; lifecycle timeline **PROD-482** |
| **Narration (before send)** | “Here the user asks if report export is **available**. Slack may surface an older **enabled** message—but lifecycle says **disabled** is current.” |
| **Narration (after result)** | “The label is **SUPERSEDED** because **PROD-482** supersedes the older enabled record—not because the model ‘feels’ the answer is wrong.” |
| **Cursor** | Keep status header, **PROD-482**, and Slack evidence links in frame |
| **Zoom** | Slack **125–150%** |
| **Max wait** | **20 s** after send for live RTS + OpenAI + MCP |
| **Retake if** | Wrong label; PROD-482 missing; private content; pasted output |
| **Fallback** | If still pending at 20 s, say “waiting on live services” once, then **stop and retake** |

---

<a id="scene-2-current"></a>

## 1:05–1:28 — Scene 2: CURRENT

| Field | Detail |
| --- | --- |
| **Screen** | Same channel; **new** message or thread (fresh `action_token`) |
| **Exact query** | `Is report export disabled on the Starter plan?` |
| **Expected result** | Header **Current**; lifecycle timeline **PROD-482** |
| **Narration** | “Same topic, opposite stated value. **Disabled** matches the current lifecycle record—so the label is **CURRENT** on the same **PROD-482** evidence.” |
| **Cursor** | **Current** header + **PROD-482** visible |
| **Zoom** | 125–150% |
| **Max wait** | **18 s** |
| **Retake if** | SUPERSEDED or wrong PROD ID; truncated response |
| **Fallback** | Retake with new mention/DM if action token stale |

---

<a id="scene-3-no-claim"></a>

## 1:28–1:45 — Scene 3: safe guidance (no claim invented)

| Field | Detail |
| --- | --- |
| **Screen** | Slack thread |
| **Exact query** | `Tell me about report export on the Starter plan.` |
| **Expected result** | Guidance block listing **supported claim families** and example questions — **no** validity header |
| **Narration** | “This is informational—no explicit proposition. TruthExpiry shows what it **can** validate and refuses to invent a label.” |
| **Cursor** | Supported-topics list + absence of Superseded/Current header |
| **Zoom** | 125–150% |
| **Max wait** | **15 s** |
| **Retake if** | A validity label appears on a structured claim |
| **Fallback** | Describe behavior; do not read the full guidance list aloud |

---

## 1:45–2:08 — Scene 4: numeric lifecycle proof

| Field | Detail |
| --- | --- |
| **Screen** | Slack thread |
| **Exact query** | `Is the API rate limit 100 requests for Starter?` |
| **Expected result** | **Superseded**; lifecycle timeline **PROD-511** |
| **Narration** | “The query states an explicit numeric value—**100**. Lifecycle shows **50** is current, so the claim is **SUPERSEDED** on **PROD-511**.” |
| **Cursor** | Superseded header, **PROD-511**, stated value visible |
| **Zoom** | 125–150% |
| **Max wait** | **18 s** |
| **Retake if** | CURRENT or wrong record |
| **Fallback** | Confirm rate-limit seed messages exist ([demo README](README.md)) |

**Prerequisite:** Run `scripts/seed_demo_workspace.py` before recording.

---

<a id="scene-5-record-flip"></a>

## 2:08–2:28 — Scene 5: live record flip (hero beat)

| Field | Detail |
| --- | --- |
| **Screen** | Return to Scene 1 thread **or** re-run Scene 1 query in a fresh thread |
| **Action** | Slowly highlight, in order: (1) **Stated in Slack** value, (2) **Slack evidence** permalink, (3) **Lifecycle timeline** `PROD-482`, (4) authority footnote |
| **Narration** | “Slack still says **enabled**. The lifecycle record **PROD-482** is authoritative and says **disabled**. TruthExpiry flips the verdict to **SUPERSEDED**—that is the product moment.” |
| **Cursor** | Pause on **PROD-482** for at least 3 seconds |
| **Zoom** | **150%** on lifecycle timeline block |
| **Max wait** | 20 s (reuse prior result — no re-query required if thread still visible) |
| **Retake if** | Timeline or PROD ID not readable; narration contradicts on-screen labels |
| **Fallback** | Use `hero-superseded.png` from [shot-list](shot-list.md) only as a still in post — prefer live Slack for submission video |

This scene replaces the former **operational proof** segment in the primary 2:50 cut. Judges care about the validity flip, not curl output.

---

## 2:28–2:50 — Close

| Field | Detail |
| --- | --- |
| **Screen** | Slack SUPERSEDED crop or architecture thumbnail — no secrets |
| **Narration** | “TruthExpiry gives hackathon judges a **sandbox workspace** with seeded evidence and seven claim families. **The model extracts. Deterministic systems decide what is still valid.**” |
| **Max wait** | 22 s |
| **Retake if** | Closing claims universal truth or undeployed production URL |
| **Do not claim** | Final video URL, `v1.0.0` tag, or signed live acceptance |

---

## Supplementary clips (not in primary 2:50 video)

### Operational health proof (optional)

| Field | Detail |
| --- | --- |
| **Screen** | Terminal with **large font**; bounded `curl` / `Invoke-WebRequest` only |
| **Action** | Worker and MCP `/healthz` + `/readyz` → **200** |
| **When** | Technical proof gallery or README — not required in main video |

### MCP outage recovery (optional)

| Field | Detail |
| --- | --- |
| **Action** | Stop MCP → worker `/readyz` → **503** → restart MCP → **200** without worker restart |
| **When** | Separate clip only — see [shot-list](shot-list.md) `mcp-recovery-optional.png` |

---

## Recording layout guidance

| Setting | Guidance |
| --- | --- |
| Slack zoom | **125–150%** where labels remain readable |
| Workspace chrome | Hide switcher where possible; crop unrelated channels |
| Frame | Status header, lifecycle ID (PROD-*), and evidence links in view |
| **Never show** | `.env`, tokens, `printenv`, Authorization headers, private channels |
| Notifications | Disabled |
| Channel naming | Prefer synthetic names (e.g. `#truthexpiry-demo`) |
| Playback | No extreme speed-up that obscures labels |

---

<a id="latency-handling"></a>

## Latency handling

| Situation | Action |
| --- | --- |
| Brief pause (&lt; 10 s) | Optional: “Live RTS and extraction in progress.” |
| 10–20 s | Wait silently with loading status visible |
| &gt; max wait for scene | **Retake** — do not splice another query’s output |
| Edit in post | Cut dead air only — **never** replace Slack body text |

---

<a id="backup-mode-disclosure"></a>

## Backup-mode disclosure

Read **before** showing product output if not on `live` profile.

### Backup A (`backup-a`)

> “For this backup take, Slack search and lifecycle validation are **live**, while claim extraction is running in the **deterministic fake adapter**. Labels still come from lifecycle evidence.”

### Backup B (`backup-b`)

> “This is the **repository fallback path** showing the deterministic pipeline and acceptance tests—not a live Slack interaction.”

---

## Per-scene quick reference

| Scene | Query | Expected outcome | Lifecycle ID |
| --- | --- | --- | --- |
| 1 | Is report export available on the Starter plan? | SUPERSEDED | PROD-482 |
| 2 | Is report export disabled on the Starter plan? | CURRENT | PROD-482 |
| 3 | Tell me about report export on the Starter plan. | Guidance — no validity label | — |
| 4 | Is the API rate limit 100 requests for Starter? | SUPERSEDED | PROD-511 |
| 5 | (reuse Scene 1 result) | Highlight record flip | PROD-482 |

---

## Truthfulness rules (non-negotiable)

- No edited Slack output presented as live.
- No lifecycle JSON edits for labels.
- No fake extractor presented as OpenAI without Backup A disclosure.
- No private Slack content on screen.
- No silent profile switching.

Live acceptance remains **unsigned** until completed in [live-acceptance.md](live-acceptance.md).
