import logging
import sys

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

from adapters.composition import build_pipeline
from listeners import register_listeners
from truthexpiry.config import ConfigError, SlackWorkerSettings
from truthexpiry.ops.health import WorkerReadinessState, start_worker_health_server
from truthexpiry.ops.logging import configure_logging
from truthexpiry.ops.metrics import init_metrics, metrics_or_noop
from truthexpiry.ops.readiness import wait_for_mcp_readiness
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
            timeout=settings.slack_timeout_seconds,
        )
        app = App(client=client)
    else:
        app = App(
            token=bot_token,
            client=WebClient(
                token=bot_token,
                timeout=settings.slack_timeout_seconds,
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
    configure_logging(settings)

    shutdown = init_shutdown_coordinator(
        drain_timeout_seconds=settings.shutdown_drain_seconds,
    )

    app, handler = create_slack_application(settings)
    pipeline = build_pipeline(slack_client=app.client, settings=settings)
    register_listeners(app, pipeline)

    socket_monitor = SocketModeConnectionMonitor(handler, readiness)
    socket_monitor.start()

    if not settings.use_fakes:
        mcp_url = settings.lifecycle_mcp_url
        auth_token = (
            settings.lifecycle_mcp_auth_token.get_secret()
            if settings.lifecycle_mcp_auth_token is not None
            else None
        )
        if mcp_url and wait_for_mcp_readiness(
            mcp_url=mcp_url,
            auth_token=auth_token,
            timeout_seconds=settings.mcp_readiness_timeout_seconds,
            client_timeout_seconds=settings.mcp_client_timeout_seconds,
        ):
            readiness.set_lifecycle_mcp("ok")
        else:
            readiness.set_lifecycle_mcp("unavailable")
            logger.error("Lifecycle MCP readiness check failed before startup")
            health_server.stop()
            raise SystemExit(1)

    metrics_or_noop().set_ready("slack-worker", readiness.is_ready())

    def _shutdown() -> None:
        socket_monitor.stop()
        handler.close()
        shutdown.wait_for_drain()
        health_server.stop()
        metrics_or_noop().set_ready("slack-worker", False)

    shutdown.install_signal_handlers(_shutdown)

    try:
        handler.start()
    finally:
        _shutdown()


if __name__ == "__main__":
    main()
