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
| Scene 1 — SUPERSEDED | 0:32–1:07 | 0:35 |
| Scene 2 — CURRENT | 1:07–1:31 | 0:24 |
| Scene 3 — no claim | 1:31–1:49 | 0:18 |
| Scene 4 — numeric SUPERSEDED | 1:49–2:12 | 0:23 |
| Operational proof | 2:12–2:30 | 0:18 |
| Close | 2:30–2:50 | 0:20 |
| **Total (target)** | | **2:50** |

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

## 0:32–1:07 — Scene 1: SUPERSEDED

| Field | Detail |
| --- | --- |
| **Screen** | Public demo channel; TruthExpiry thread |
| **Exact query** | `Is report export available on the Starter plan?` |
| **Expected result** | Validity label **SUPERSEDED**; lifecycle evidence **PROD-482**; explanation that disabled supersedes enabled (PROD-481) |
| **Narration (before send)** | “Here the user asks if report export is **available**. Slack may surface an older **enabled** message—but lifecycle says **disabled** is current.” |
| **Narration (after result)** | “The label is **SUPERSEDED** because **PROD-482** supersedes the older enabled record—not because the model ‘feels’ the answer is wrong.” |
| **Cursor** | Keep **SUPERSEDED**, **PROD-482**, and evidence lines in frame |
| **Zoom** | Slack **125–150%** |
| **Max wait** | **22 s** after send for live RTS + OpenAI + MCP (must fit inside 35 s segment) |
| **Retake if** | Wrong label; PROD-482 missing; private content; pasted output |
| **Fallback** | If still pending at 22 s, say “waiting on live services” once, then **stop and retake** — do not cut to fabricated output |

---

<a id="scene-2-current"></a>

## 1:07–1:31 — Scene 2: CURRENT

| Field | Detail |
| --- | --- |
| **Screen** | Same channel; **new** message or thread (fresh `action_token`) |
| **Exact query** | `Is report export disabled on the Starter plan?` |
| **Expected result** | **CURRENT**; lifecycle evidence **PROD-482** |
| **Narration** | “Same topic, opposite stated value. **Disabled** matches the current lifecycle record—so the label is **CURRENT** on the same **PROD-482** evidence.” |
| **Cursor** | **CURRENT** + **PROD-482** visible |
| **Zoom** | 125–150% |
| **Max wait** | **18 s** |
| **Retake if** | SUPERSEDED or wrong PROD ID; truncated response |
| **Fallback** | Retake with new mention/DM if action token stale |

---

<a id="scene-3-no-claim"></a>

## 1:31–1:49 — Scene 3: no claim invented

| Field | Detail |
| --- | --- |
| **Screen** | Slack thread |
| **Exact query** | `Tell me about report export on the Starter plan.` |
| **Expected result** | **No structured claim**; **no** CURRENT/SUPERSEDED/CONFLICTING/UNVERIFIED label on a claim. Response category: empty results with message indicating **no structured claims were extracted** (see pipeline formatter) |
| **Narration** | “This is informational—no explicit proposition. The safe answer is **not to invent a value** or force a validity label.” |
| **Cursor** | Show absence of status label block |
| **Zoom** | 125–150% |
| **Max wait** | **18 s** |
| **Retake if** | A validity label appears on a structured claim |
| **Fallback** | Do not narrate exact response prose; describe behavior only |

---

## 1:49–2:12 — Scene 4: numeric lifecycle proof

| Field | Detail |
| --- | --- |
| **Screen** | Slack thread |
| **Exact query** | `Is the API rate limit 100 requests for Starter?` |
| **Expected result** | **SUPERSEDED**; lifecycle evidence **PROD-511**; canonical current value **50** supersedes **100** (PROD-510) |
| **Narration** | “The query states an explicit numeric value—**100**. Lifecycle shows **50** is current, so the claim is **SUPERSEDED** on **PROD-511**.” |
| **Cursor** | **SUPERSEDED**, **PROD-511**, numeric context visible |
| **Zoom** | 125–150% |
| **Max wait** | **18 s** |
| **Retake if** | CURRENT or wrong record; evidence messages 3–4 missing from channel |
| **Fallback** | Confirm public messages for PROD-510/511 exist ([demo README](README.md)) |

**Prerequisite:** Post rate-limit evidence messages before recording (see [README — channel setup](README.md#dedicated-slack-demo-channel-setup)).

---

<a id="operational-proof"></a>

## 2:12–2:30 — Operational proof

**Recommendation:** Use **Option A** in the **primary 2:50 video**. Option B belongs in a **separate technical clip** or screenshots — it risks overruns and live failure.

### Option A — static health proof (recommended for main video)

| Field | Detail |
| --- | --- |
| **Screen** | Terminal with **large font**; `curl` or `Invoke-WebRequest` only — **no `.env`** |
| **Action** | Show bounded JSON status codes only: |
| | Worker `GET http://127.0.0.1:8080/healthz` → **200** |
| | Worker `GET http://127.0.0.1:8080/readyz` → **200** |
| | MCP `GET http://127.0.0.1:8001/healthz` → **200** |
| | MCP `GET http://127.0.0.1:8001/readyz` → **200** |
| **Narration** | “Worker and lifecycle MCP are independently deployable. Readiness is green before we queried Slack.” |
| **Max wait** | **15 s** total for four probes |
| **Retake if** | Token in URL; response body shows secrets or message content |
| **Must hide** | Environment variables, auth headers, full URLs with credentials |

### Option B — outage recovery (separate clip or shot list only)

| Field | Detail |
| --- | --- |
| **Screen** | Terminal + optional readiness JSON |
| **Action** | Stop MCP → worker `/healthz` stays **200**, `/readyz` → **503** → restart MCP → `/readyz` → **200** **without** worker restart |
| **When to use** | Supplementary proof — **not required** in primary 2:50 video |
| **Risk** | Timing overrun; ambiguous narration — prefer [shot-list](shot-list.md) still capture |

---

## 2:30–2:50 — Close

| Field | Detail |
| --- | --- |
| **Screen** | Slack result montage or architecture thumbnail — no secrets |
| **Narration** | “TruthExpiry turns Slack memory into lifecycle-aware evidence. **The model extracts. Deterministic systems decide what is still valid.**” |
| **Max wait** | 20 s |
| **Retake if** | Closing claims “universal truth” or live deployment exists |
| **Do not claim** | Final video URL, `v1.0.0` tag, or signed live acceptance |

---

## Recording layout guidance

| Setting | Guidance |
| --- | --- |
| Slack zoom | **125–150%** where labels remain readable |
| Workspace chrome | Hide switcher where possible; crop unrelated channels |
| Frame | Status label, lifecycle ID (PROD-*), and evidence explanation in view |
| Terminal | Large font for health proof; single-purpose window |
| **Never show** | `.env`, tokens, `printenv`, Authorization headers, private channels |
| Notifications | Disabled |
| Browser | Close email, calendar, personal tabs |
| Channel naming | Prefer synthetic names (e.g. `#product-demo-public`) |
| Playback | No extreme speed-up that obscures labels |

---

<a id="latency-handling"></a>

## Latency handling

| Situation | Action |
| --- | --- |
| Brief pause (&lt; 10 s) | Optional: “Live RTS and extraction in progress.” |
| 10–25 s | Wait silently with loading visible; do not fill with unrelated talk |
| &gt; max wait for scene | **Retake** the scene — do not splice another query’s output |
| Edit in post | Cut dead air only — **never** replace Slack body text |
| Profile switch | **Forbidden** without on-screen disclosure and new take |

---

<a id="backup-mode-disclosure"></a>

## Backup-mode disclosure

Read **before** showing product output if not on `live` profile.

### Backup A (`backup-a`)

> “For this backup take, Slack search and lifecycle validation are **live**, while claim extraction is running in the **deterministic fake adapter**. Labels still come from lifecycle evidence.”

### Backup B (`backup-b`)

> “This is the **repository fallback path** showing the deterministic pipeline and acceptance tests—not a live Slack interaction.”

Do not use backup modes for the primary submission video without platform permission and clear disclosure.

---

## Per-scene quick reference

| Scene | Query | Expected label / outcome | Lifecycle ID |
| --- | --- | --- | --- |
| 1 | Is report export available on the Starter plan? | SUPERSEDED | PROD-482 |
| 2 | Is report export disabled on the Starter plan? | CURRENT | PROD-482 |
| 3 | Tell me about report export on the Starter plan. | No structured claim | — |
| 4 | Is the API rate limit 100 requests for Starter? | SUPERSEDED | PROD-511 |

---

## Truthfulness rules (non-negotiable)

- No edited Slack output presented as live.
- No lifecycle JSON edits for labels.
- No fake extractor presented as OpenAI without Backup A disclosure.
- No private Slack content on screen.
- No hardcoded labels in narration that contradict on-screen output.
- No silent profile switching.
- No pre-recorded Slack pasted into the timeline.

Live acceptance remains **unsigned** until completed in [live-acceptance.md](live-acceptance.md).
