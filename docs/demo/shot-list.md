# TruthExpiry demo shot list

Capture checklist for screenshots, architecture exports, and supplementary proof. **No binary assets are committed in this slice** — record captures locally and track metadata here.

**Script:** [recording-script.md](recording-script.md) · **Export commands:** [../assets/README.md](../assets/README.md)

---

## Capture table

| ID | Filename | Type | Exact content | Profile | Crop / dimensions | Must show | Must hide | Destination | Captured | Approved |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1 | `hero-superseded.png` | Screenshot | Scene 1 query + **SUPERSEDED** + **PROD-482** | `live` | Landscape; README-width readable | Query, label, lifecycle ID, evidence context | Tokens, unrelated channels, PII | README hero, submission gallery | | |
| S2 | `current-example.png` | Screenshot | Scene 2 query + **CURRENT** + **PROD-482** | `live` | Same as S1 | Query, CURRENT, PROD-482 | Secrets, workspace clutter | README examples, submission gallery | | |
| S3 | `no-claim-safety.png` | Screenshot | Scene 3 — no validity label / no structured claim | `live` | Same as S1 | Informational query, absence of label | Fabricated “no claim” text overlay | README examples, submission gallery | | |
| S4 | `truthexpiry-architecture.svg` | Export | Architecture diagram from Mermaid source | N/A (diagram) | Vector; full labels visible | Probabilistic vs deterministic zones | URLs, tokens | README, submission, video overlay | | |
| S5 | `truthexpiry-architecture-16x9.png` | Export | Architecture raster 1920×1080 | N/A (diagram) | 16:9 white background | Same as S4 | Cropped labels | Slides, video b-roll | | |
| S6 | `health-readiness.png` | Screenshot | Option A health proof — HTTP **200** on four probes | `live` | Terminal large font | `status` / ok bounded JSON | `.env`, tokens, auth headers | Technical proof, optional video | | |
| S7 | `ci-green.png` | Screenshot | Successful CI workflows (`tests`, `ruff`, `security`, `containers`) | N/A | Crop to workflow names + green check | Workflow identity | Repo admin settings, tokens | Technical proof, submission | | |
| S8 | `metrics-optional.png` | Screenshot | Bounded metrics labels only (if enabled) | `live` | Crop to metric names | `service`, `outcome`, `failure_category` | High-cardinality labels | Technical proof (optional) | | |
| S9 | `hackathon-thumbnail.png` | Thumbnail | Title + tagline or SUPERSEDED crop | `live` or design | `<PLATFORM_REQUIRED_DIMENSIONS>` | “Similarity is not validity” or product proof | Secrets, private data | Devpost / platform thumbnail | | |

---

## Asset details

### S1 — hero-superseded.png

- **Source scene:** [recording-script Scene 1](recording-script.md#scene-1-supereded)
- **Query:** `Is report export available on the Starter plan?`
- **Truth metadata:** profile, commit SHA, date, live (not composited)

### S2 — current-example.png

- **Source scene:** [recording-script Scene 2](recording-script.md#scene-2-current)
- **Query:** `Is report export disabled on the Starter plan?`

### S3 — no-claim-safety.png

- **Source scene:** [recording-script Scene 3](recording-script.md#scene-3-no-claim)
- **Query:** `Tell me about report export on the Starter plan.`
- **Do not** overlay fake UI text; capture live Slack output only

### S4 / S5 — architecture exports

Generate per [../assets/README.md](../assets/README.md):

```powershell
npx -y @mermaid-js/mermaid-cli -i docs/architecture/truthexpiry-architecture.mmd -o docs/assets/truthexpiry-architecture.svg -b transparent
npx -y @mermaid-js/mermaid-cli -i docs/architecture/truthexpiry-architecture.mmd -o docs/assets/truthexpiry-architecture-16x9.png -b white -w 1920 -H 1080
```

Verify labels are not cropped before marking approved.

### S6 — health-readiness.png

- **Source:** [recording-script Option A](recording-script.md#operational-proof)
- Show only bounded probe output; redact host if needed — **never** redact query/label/PROD-* in product screenshots (S1–S3)

### S7 — ci-green.png

- Workflows: `tests.yml`, `ruff.yml`, `security.yml`, `containers.yml`
- Do not expose unrelated repository or account administration

### S8 — metrics-optional.png

- Requires `TRUTH_EXPIRY_METRICS_ENABLED=1`
- Skip if metrics not used in demo

### S9 — hackathon-thumbnail.png

- Dimensions: `<PLATFORM_REQUIRED_DIMENSIONS>` — fill when platform publishes requirements
- Do not commit until dimensions confirmed

---

## Screenshot truthfulness metadata

For each product screenshot (S1–S3, S6 if live), record in your local capture log:

| Field | Example |
| --- | --- |
| Profile | `live` |
| Commit SHA | `<RECORDING_COMMIT_SHA>` |
| Date | `<RECORDING_DATE>` |
| Live vs diagram | Live Slack / terminal |
| Crop applied | Yes — describe bounds |
| Redaction applied | Only for secrets — **not** for query, label, lifecycle ID, or evidence meaning |

**Allowed:** crop, blur sidebar, redact tokens.  
**Forbidden:** composite false labels, paste fake Slack text, edit PROD-* IDs.

---

## Frame-by-frame privacy review

Before marking any asset **Approved**, confirm:

- [ ] No Slack bot token (`xoxb-…`)
- [ ] No Slack app token (`xapp-…`)
- [ ] No OpenAI API key (`sk-…`)
- [ ] No MCP bearer token
- [ ] No `action_token`
- [ ] No `.env` file or editor tab
- [ ] No private-channel names
- [ ] No private message bodies
- [ ] No email addresses (unless intentionally public)
- [ ] No notification banners with personal data
- [ ] No terminal history with `export`, `set`, or secret values
- [ ] No credential-bearing URLs
- [ ] No unrelated browser tabs
- [ ] No raw OpenAI provider output
- [ ] No raw logs with query or evidence content

---

## Future asset destinations

| Asset | Intended use |
| --- | --- |
| S1 `hero-superseded.png` | README hero (`<!-- M5_MEDIA -->` insertion point) |
| S2, S3 | README example row illustrations |
| S4, S5 | README architecture, submission gallery, video b-roll |
| S6 | Technical proof, optional video segment |
| S7 | Technical proof, submission gallery |
| S8 | Technical proof (optional) |
| S9 | Platform thumbnail |

Do not add image links to README until files exist and privacy review passes.

---

## Optional supplementary captures

| Content | Suggested filename | Notes |
| --- | --- | --- |
| MCP outage recovery (Option B) | `mcp-recovery-optional.png` | Separate from primary 3:00 video |
| Scene 4 numeric SUPERSEDED | `superseded-rate-limit.png` | Optional README / gallery |
| Preflight `READY TO RECORD` | `preflight-ready.png` | Redact paths if sensitive; no env values |

---

## Platform placeholders

| Placeholder | Purpose |
| --- | --- |
| `<PLATFORM_REQUIRED_DIMENSIONS>` | Thumbnail width × height |
| `<RECORDING_COMMIT_SHA>` | Screenshot truth metadata |
| `<RECORDING_DATE>` | Screenshot truth metadata |
| `<DEMO_VIDEO_URL>` | Link after upload — not claimed in this slice |
