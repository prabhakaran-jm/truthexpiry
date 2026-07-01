# TruthExpiry demo and submission assets

This directory documents **planned** media assets for the M5 hackathon submission. Commit 2 adds export guidance only — no binary placeholders are committed.

## Planned asset filenames

| File | Purpose |
|------|---------|
| `truthexpiry-architecture.svg` | Primary architecture diagram (vector) |
| `truthexpiry-architecture-16x9.png` | Slide-friendly architecture raster |
| `hero-superseded.png` | Demo screenshot: SUPERSEDED example |
| `current-example.png` | Demo screenshot: CURRENT example |
| `no-claim-safety.png` | Demo screenshot: informational / no-claim path |
| `health-readiness.png` | Operational screenshot: health and readiness probes |
| `ci-green.png` | CI verification screenshot |

Store generated files here when captured during M5 media work. Do not commit secrets or private Slack content.

## Architecture diagram export

### Source

Mermaid source: [`docs/architecture/truthexpiry-architecture.mmd`](../architecture/truthexpiry-architecture.mmd)

### Recommended commands

Requires Node.js `npx` (no Node dependency is added to the Python project).

```powershell
# SVG (primary vector export)
npx -y @mermaid-js/mermaid-cli `
  -i docs/architecture/truthexpiry-architecture.mmd `
  -o docs/assets/truthexpiry-architecture.svg `
  -b transparent

# 16:9 PNG for slides (light background recommended for readability)
npx -y @mermaid-js/mermaid-cli `
  -i docs/architecture/truthexpiry-architecture.mmd `
  -o docs/assets/truthexpiry-architecture-16x9.png `
  -b white `
  -w 1920 `
  -H 1080
```

### Export settings

| Setting | Recommendation |
|---------|----------------|
| SVG target | `docs/assets/truthexpiry-architecture.svg` |
| PNG target | `docs/assets/truthexpiry-architecture-16x9.png` |
| Width | 1920 px for slide PNG |
| Background | Transparent for SVG; white for PNG slides |
| Minimum readable font | 14 px equivalent after export; re-export wider if labels crowd |
| Cropping check | Open the export and confirm subgraph titles, callout boxes, and boundary labels are fully visible |
| Regeneration | Re-run the commands above after any edit to `truthexpiry-architecture.mmd` |

### Verify export quality

1. Zoom to 100% and confirm **Probabilistic extraction**, **Deterministic validation**, and **Operational controls** are legible.
2. Confirm the diagram does **not** show the LLM assigning validity labels.
3. Confirm no tokens, URLs, or environment values appear in the image.
4. Compare against [`docs/submission/technical-proof.md`](../submission/technical-proof.md) if flow semantics change.

## Screenshot capture rules

Captured assets must **not** expose:

- Slack bot token (`xoxb-…`)
- Slack app token (`xapp-…`)
- OpenAI API key (`sk-…`)
- MCP bearer token
- Slack `action_token`
- `.env` files or editor tabs showing secrets
- Terminal history containing secret exports
- Private-channel names or membership
- Private user information
- Raw private messages
- Credential-bearing URLs
- Internal provider response bodies

### Safe capture practices

- Use a **dedicated synthetic public demo channel** with invented PROD-* references only.
- Crop the Slack UI to the demo thread; exclude unrelated workspace sidebars and DMs.
- Use placeholder URLs in submission copy until final links are known.
- Run [`scripts/demo_preflight.py`](../../scripts/demo_preflight.py) before recording; never paste preflight JSON containing environment mappings.
- Blur or omit any accidental secret before saving an asset.

## Relationship to tests

Generated SVG/PNG files are **not** required for `pytest`. Architecture accuracy is enforced by documentation review and optional manual export checks.
