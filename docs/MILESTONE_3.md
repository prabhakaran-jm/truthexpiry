# TruthExpiry Milestone 3 — Live claim extraction

Milestone 3 replaces the hard-coded production `FakeClaimExtractionPort` with an independently selectable OpenAI-backed extractor while preserving deterministic lifecycle labeling.

## Architecture

```text
Slack app_mention or message.im event
    → listener
    → TruthExpiryPipeline
    → SlackRtsAdapter (M2, unchanged)
    → EphemeralRtsHits
    → PydanticAiClaimExtractionAdapter (when TRUTH_EXPIRY_CLAIM_EXTRACTOR=live)
    → domain claim-schema validation
    → LifecycleMcpAdapter (M1/M2, unchanged)
    → deterministic labeler
    → Slack response
```

**Invariant:** The model extracts zero or one structured claim. The deterministic labeler alone assigns `CURRENT`, `SUPERSEDED`, `CONFLICTING`, or `UNVERIFIED`.

## Provider

- **OpenAI only** in M3
- Model: `openai:gpt-4.1-mini`
- Credential: `OPENAI_API_KEY` (required when `TRUTH_EXPIRY_CLAIM_EXTRACTOR=live`)
- Fixed **20-second** provider timeout
- **No automatic retry** in M3

## Composition precedence

1. Explicit injected `llm` dependency (tests / callers)
2. `TRUTH_EXPIRY_USE_FAKES=1` → `FakeClaimExtractionPort` (ignores extractor selector)
3. `TRUTH_EXPIRY_CLAIM_EXTRACTOR=fake|live`
4. Selector unset → default `fake`

Supported mixed mode: live Slack RTS + live lifecycle MCP + fake claim extraction (default until `TRUTH_EXPIRY_CLAIM_EXTRACTOR=live`).

## Structured output

The model returns strict JSON validated as:

- `claim: null` for no extractable proposition
- or one `claim` object with `entity`, `attribute`, `scope`, `stated_value`, `evidence_ids`

The model must not return validity labels, permalinks, or lifecycle ticket IDs.

## Evidence grounding

- Request-local opaque IDs: `evidence-1`, `evidence-2`, …
- Model receives only opaque ID + bounded primary message content
- Adapter maps selected IDs to sanitized `EvidenceRef` values via `rts_sanitizer`
- Evidence may clarify entity/attribute/scope for model-extracted claims; it must not supply missing proposition polarity

## Deterministic query-grounding fallback

OpenAI is the primary live claim extractor. A narrow **deterministic query-grounding fallback** runs only when the provider successfully returns an explicit `{"claim": null}`.

- The fallback uses **query text only** to derive entity, attribute, scope, and stated value
- It does **not** inspect Slack evidence, lifecycle records, or provider prose
- Evidence is attached afterward as sanitized source references only (up to 3 RTS hits, RTS order)
- Provider timeouts, transport failures, malformed output, and invalid model claims do **not** activate the fallback
- The deterministic labeler alone assigns `CURRENT`, `SUPERSEDED`, `CONFLICTING`, or `UNVERIFIED`

Not every successful claim was produced by the LLM; null-provider responses with a fully grounded explicit query may use this fallback.

## Data sent to the provider

- User query (max 500 characters; longer queries fail closed)
- Up to 8 evidence snippets (400 chars each, 3000 total budget)
- Primary message content only

## Data never sent

- Permalinks, channel IDs, user IDs, timestamps
- Action tokens, bot/app tokens
- Lifecycle ticket IDs
- Complete Slack events or API responses
- Context-before / context-after messages

## Local startup (three-process live path)

```powershell
# Terminal 1 — lifecycle MCP
python -m lifecycle_mcp.server

# Terminal 2 — Slack app
$env:TRUTH_EXPIRY_LIFECYCLE_MCP_URL = "http://127.0.0.1:8000/mcp"
$env:TRUTH_EXPIRY_CLAIM_EXTRACTOR = "live"
$env:OPENAI_API_KEY = "sk-..."
# unset TRUTH_EXPIRY_USE_FAKES
python app.py
```

## Manual acceptance

| Query | Expected |
|-------|----------|
| `Is report export available on the starter plan?` | `SUPERSEDED` (`PROD-482`) |
| `Is report export disabled on the starter plan?` | `CURRENT` (`PROD-482`) |
| `Tell me about report export on the starter plan.` | No structured claim |
| `Is the API rate limit 100 requests for starter?` | `SUPERSEDED` (`PROD-511`) |
| `Is the API rate limit 50 requests for starter?` | `CURRENT` (`PROD-511`) |
| `What is the API rate limit for starter?` | No structured claim |

## Exclusions (M3)

No changes to: Slack RTS adapter, lifecycle MCP, labeler, private-channel search, OAuth, pagination, deployment, caching, or persistence.

## Tests

`pytest -q` runs with `TRUTH_EXPIRY_USE_FAKES=1` and makes **no production network calls**. Live extraction is tested via `tests/fakes/extraction_runner.py`.
