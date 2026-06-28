from datetime import date

import pytest

from adapters.composition import build_pipeline, reset_pipeline
from truthexpiry.ports.clock import ClockPort


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
def evaluation_date() -> date:
    return date(2024, 6, 15)


@pytest.fixture
def fixed_clock(evaluation_date: date) -> FixedClock:
    return FixedClock(evaluation_date)


@pytest.fixture
def pipeline(fixed_clock: FixedClock):
    return build_pipeline(clock=fixed_clock, use_fakes=True)


@pytest.fixture
def no_fake_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRUTH_EXPIRY_USE_FAKES", raising=False)
    reset_pipeline()
