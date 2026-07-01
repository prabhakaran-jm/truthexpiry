# Socket Mode connection state (M4 Step 0)

TruthExpiry pins `slack-bolt==1.28.0` / `slack-sdk==3.42.0`. Operational readiness uses the
**builtin** `SocketModeHandler`, which exposes a `client: SocketModeClient` (sync builtin
implementation).

## Public API inspected

| Symbol | Module | Notes |
|--------|--------|-------|
| `SocketModeHandler` | `slack_bolt.adapter.socket_mode` | `start()`, `close()`, `connect()`, `disconnect()`, `handle()` |
| `SocketModeHandler.client` | builtin handler | `slack_sdk.socket_mode.builtin.client.SocketModeClient` |
| `SocketModeClient.is_connected()` | `slack_sdk.socket_mode.builtin.client` | Returns `bool`; used for readiness |

There is **no** `is_connected` on `SocketModeHandler` itself. Readiness code must call
`handler.client.is_connected()`.

## Approach in `truthexpiry.ops.socket_mode`

1. Wrap the handler in `SocketModeConnectionMonitor` after construction.
2. Poll `client.is_connected()` on a background interval (configurable, default 2s).
3. Update `WorkerReadinessState.socket_mode`:
   - `connecting` before the first successful connection
   - `ok` while connected
   - `disconnected` after a previously established connection is lost, or on monitor stop
4. Reconnect metric and log fire only on `disconnected` → `ok` transitions (not the initial connect).
5. On shutdown (`handler.close()`), mark `disconnected`.

Bolt's `auto_reconnect_enabled=True` (default) means transient disconnects may flip readiness to
`503` until reconnect completes. Liveness (`/healthz`) stays `200` as long as the process responds.

## Out of scope

- No changes to Bolt listener registration or event payloads.
- No persistence of connection history beyond in-memory readiness state.
