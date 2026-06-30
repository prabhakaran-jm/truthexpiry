# Secrets rotation runbook

## Slack tokens

1. Rotate `SLACK_APP_TOKEN` and `SLACK_BOT_TOKEN` in the Slack app settings.
2. Update platform secret store entries.
3. Rolling restart worker pods/processes one at a time.
4. Confirm `/readyz` returns 200 and Socket Mode reconnects.

## MCP bearer token

1. Generate new `TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN`.
2. Update MCP server environment and restart MCP.
3. Update worker environment with the same token; restart worker.
4. Verify worker MCP readiness check passes.

## OpenAI API key

1. Rotate key in OpenAI dashboard.
2. Update `OPENAI_API_KEY` in worker secret store.
3. Restart worker only (MCP unaffected).
4. Run a live extraction smoke query in staging.

## Verification

- Error messages name variables only; never log rotated values.
- `python app.py --check` must not require any secret values.
