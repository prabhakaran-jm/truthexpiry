import logging
import sys
import threading

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

from adapters.composition import build_pipeline
from listeners import register_listeners
from truthexpiry.config import ConfigError, SlackWorkerSettings
from truthexpiry.ops.event_dedup import init_event_dedup_cache, reset_event_dedup_cache
from truthexpiry.ops.health import WorkerReadinessState, start_worker_health_server
from truthexpiry.ops.logging import configure_logging
from truthexpiry.ops.mcp_health import lifecycle_mcp_health_readyz_url
from truthexpiry.ops.mcp_readiness_monitor import McpReadinessMonitor
from truthexpiry.ops.metrics import (
    init_metrics,
    metrics_or_noop,
    start_metrics_server,
    stop_metrics_server,
)
from truthexpiry.ops.shutdown import init_shutdown_coordinator
from truthexpiry.ops.socket_mode import SocketModeConnectionMonitor
from truthexpiry.ops.structural_check import parse_cli_args, run_structural_check

load_dotenv(dotenv_path=".env", override=False)

logger = logging.getLogger(__name__)


def create_slack_application(
    settings: SlackWorkerSettings,
) -> tuple[App, SocketModeHandler]:
    """Construct Bolt App and SocketModeHandler from validated settings."""
    bot_token = settings.slack_bot_token.get_secret()  # type: ignore[union-attr]
    app_token = settings.slack_app_token.get_secret()  # type: ignore[union-attr]

    if settings.slack_api_url:
        client = WebClient(
            base_url=settings.slack_api_url,
            token=bot_token,
            timeout=int(settings.slack_timeout_seconds),
        )
        app = App(client=client)
    else:
        app = App(
            token=bot_token,
            client=WebClient(
                token=bot_token,
                timeout=int(settings.slack_timeout_seconds),
            ),
        )

    handler = SocketModeHandler(app, app_token)
    return app, handler


def main() -> None:
    if parse_cli_args():
        raise SystemExit(run_structural_check())

    settings = SlackWorkerSettings.from_env()
    try:
        settings.validate_runtime()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    readiness = WorkerReadinessState()
    readiness.set_configuration("ok")
    if settings.use_fakes:
        readiness.set_lifecycle_mcp("skipped")
    else:
        readiness.set_lifecycle_mcp("not_ready")

    health_server = start_worker_health_server(
        settings.health_host,
        settings.health_port,
        readiness,
    )
    init_metrics(enabled=settings.metrics_enabled)
    if settings.metrics_enabled:
        start_metrics_server(
            settings.health_host,
            settings.metrics_port,
        )
    configure_logging(settings)
    init_event_dedup_cache(enabled=settings.dedup_event_ids)

    shutdown = init_shutdown_coordinator(
        drain_timeout_seconds=settings.shutdown_drain_seconds,
    )

    mcp_monitor: McpReadinessMonitor | None = None
    if not settings.use_fakes:
        mcp_url = settings.lifecycle_mcp_url
        if not mcp_url:
            print("TRUTH_EXPIRY_LIFECYCLE_MCP_URL is required", file=sys.stderr)
            raise SystemExit(1)
        try:
            health_readyz_url = lifecycle_mcp_health_readyz_url(
                mcp_url,
                health_url=settings.lifecycle_mcp_health_url,
                health_port=settings.lifecycle_mcp_health_port,
            )
        except ConfigError as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(1) from exc

        mcp_monitor = McpReadinessMonitor(
            readiness,
            health_readyz_url=health_readyz_url,
            timeout_seconds=settings.mcp_client_timeout_seconds,
        )

    app, handler = create_slack_application(settings)
    pipeline = build_pipeline(slack_client=app.client, settings=settings)
    register_listeners(app, pipeline)

    socket_monitor = SocketModeConnectionMonitor(handler, readiness)
    socket_monitor.start()

    if mcp_monitor is not None:
        mcp_monitor.start()

    metrics_or_noop().set_ready("slack-worker", readiness.is_ready())

    shutdown_lock = threading.Lock()
    shutdown_complete = False

    def _shutdown() -> None:
        nonlocal shutdown_complete
        with shutdown_lock:
            if shutdown_complete:
                return
            shutdown_complete = True

        readiness.set_draining(True)
        shutdown.request_shutdown()
        if mcp_monitor is not None:
            mcp_monitor.stop()
        socket_monitor.stop()
        handler.close()
        shutdown.wait_for_drain()
        health_server.stop()
        stop_metrics_server()
        metrics_or_noop().set_ready("slack-worker", False)
        reset_event_dedup_cache()

    shutdown.install_signal_handlers(_shutdown)

    try:
        handler.start()
    finally:
        _shutdown()


if __name__ == "__main__":
    main()
