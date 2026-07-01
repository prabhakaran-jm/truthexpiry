from datetime import date

import pytest

from adapters.composition import build_pipeline, reset_pipeline
from truthexpiry.ports.clock import ClockPort

_RUNTIME_ENV_VARS = (
    "TRUTH_EXPIRY_USE_FAKES",
    "TRUTH_EXPIRY_CLAIM_EXTRACTOR",
    "TRUTH_EXPIRY_LIFECYCLE_MCP_URL",
    "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN",
    "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_DISABLED",
    "TRUTH_EXPIRY_LIFECYCLE_MCP_HOST",
    "TRUTH_EXPIRY_LIFECYCLE_MCP_PORT",
    "TRUTH_EXPIRY_LIFECYCLE_MCP_HEALTH_PORT",
    "TRUTH_EXPIRY_LIFECYCLE_MCP_DATASET_PATH",
    "TRUTH_EXPIRY_HEALTH_HOST",
    "TRUTH_EXPIRY_HEALTH_PORT",
    "TRUTH_EXPIRY_LOG_LEVEL",
    "TRUTH_EXPIRY_LOG_FORMAT",
    "TRUTH_EXPIRY_SLACK_TIMEOUT_SECONDS",
    "TRUTH_EXPIRY_MCP_CLIENT_TIMEOUT_SECONDS",
    "TRUTH_EXPIRY_SHUTDOWN_DRAIN_SECONDS",
    "TRUTH_EXPIRY_MCP_SHUTDOWN_SECONDS",
    "TRUTH_EXPIRY_METRICS_ENABLED",
    "TRUTH_EXPIRY_METRICS_PORT",
    "TRUTH_EXPIRY_DEDUP_EVENT_IDS",
    "TRUTH_EXPIRY_LIFECYCLE_MCP_HEALTH_URL",
    "SLACK_BOT_TOKEN",
    "SLACK_APP_TOKEN",
    "SLACK_API_URL",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
)


class FixedClock(ClockPort):
    def __init__(self, on_date: date) -> None:
        self._on_date = on_date

    def today(self) -> date:
        return self._on_date


@pytest.fixture(autouse=True)
def fake_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUTH_EXPIRY_USE_FAKES", "1")
    reset_pipeline()
    yield
    reset_pipeline()


@pytest.fixture
def clean_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _RUNTIME_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    reset_pipeline()


@pytest.fixture
def evaluation_date() -> date:
    return date(2024, 6, 15)


@pytest.fixture
def fixed_clock(evaluation_date: date) -> FixedClock:
    return FixedClock(evaluation_date)


@pytest.fixture
def pipeline(fixed_clock: FixedClock):
    return build_pipeline(clock=fixed_clock, use_fakes=True)


@pytest.fixture
def no_fake_env(clean_runtime_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN", "test-mcp-auth-token")
    reset_pipeline()
