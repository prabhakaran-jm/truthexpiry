# TruthExpiry final live acceptance matrix

Use this record after M5 demo assets are in place and before final submission.

**Do not paste Slack message bodies, tokens, prompts, model output, or private-channel content into this record.** Use pass/fail and short safe notes only.

## Sign-off header

| Field | Value |
|-------|-------|
| Date | |
| Tester | |
| Commit / tag | |
| Profile | `live` / `backup-a` / `backup-b` |
| Preflight exit code | |
| Overall result | PASS / FAIL |

---

## Product behavior

| # | Scenario | Query / action | Expected result | Pass | Notes |
|---|----------|----------------|-----------------|------|-------|
| 1 | Stale availability claim | `Is report export available on the Starter plan?` | **SUPERSEDED**; lifecycle evidence **PROD-482** | | |
| 2 | Current availability claim | `Is report export disabled on the Starter plan?` | **CURRENT**; lifecycle evidence **PROD-482** | | |
| 3 | Informational ambiguity | `Tell me about report export on the Starter plan.` | No structured claim; no validity label | | |
| 4 | Value-less rate-limit query | `What is the API rate limit for starter?` | No structured claim | | |
| 5 | Explicit stale numeric claim | `Is the API rate limit 100 requests for Starter?` | **SUPERSEDED**; lifecycle evidence **PROD-511** | | |
| 6 | Explicit current numeric claim | `Is the API rate limit 50 requests for Starter?` | **CURRENT**; lifecycle evidence **PROD-511** | | |
| 7 | Conflicting polarity | e.g. `Is report export enabled and disabled on Starter?` | No structured claim | | |
| 8 | Empty RTS results | Query with no public evidence | Honest no-evidence / unverified handling | | |
| 9 | Private-channel exclusion | Decoy message in private channel | Private content not returned | | |

### Expected labels (from repository dataset)

**PROD-482** (`report_export` / `availability` / `disabled`, supersedes PROD-481 `enabled`):

- Query asks **available** → **SUPERSEDED**
- Query asks **disabled** → **CURRENT**

**PROD-511** (`api_rate_limit` / `max_requests` / `50`, supersedes PROD-510 `100`):

- Query states **100** → **SUPERSEDED**
- Query states **50** → **CURRENT**

## Operational behavior

| # | Check | Expected | Pass | Notes |
|---|-------|----------|------|-------|
| 10 | Worker `/healthz` | HTTP 200 | | |
| 11 | Worker `/readyz` | HTTP 200 when connected + MCP ready | | |
| 12 | MCP `/healthz` | HTTP 200 | | |
| 13 | MCP `/readyz` | HTTP 200 after dataset + tool registration | | |
| 14 | MCP outage | Stop MCP briefly | Worker stays live; worker `/readyz` → 503 | | |
| 15 | MCP recovery | Restart MCP | Worker `/readyz` → 200 without worker restart | | |
| 16 | Invalid OpenAI credential | Bad `OPENAI_API_KEY` in live mode | Generic extraction-unavailable response; no secret in output | | |
| 17 | Worker SIGTERM | Send SIGTERM during idle | `/readyz` 503; intake closes; in-flight work drains | | |
| 18 | Log privacy | Review recent logs | No query, evidence body, or token markers | | |
| 19 | Metrics privacy | If metrics enabled | Bounded labels only; no high-cardinality or sensitive labels | | |

---

## Evidence attachments (safe)

| Item | Location / reference |
|------|----------------------|
| Preflight output | |
| CI run URL | |
| Container smoke run URL | |
| Test count at freeze | |
| Screenshot filenames | |

## Reviewer certification

| Role | Name | Date | Signature / approval |
|------|------|------|----------------------|
| Demo operator | | | |
| Technical reviewer | | | |
