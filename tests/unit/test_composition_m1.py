import pytest

from adapters.composition import LiveAdaptersUnavailableError, build_pipeline
from adapters.fakes.lifecycle import FakeLifecycleEvidenceAdapter
from adapters.lifecycle_mcp.adapter import LifecycleMcpAdapter


def test_build_pipeline_uses_all_fakes_when_flag_set(fixed_clock):
    pipeline = build_pipeline(clock=fixed_clock, use_fakes=True)
    assert isinstance(pipeline._lifecycle, FakeLifecycleEvidenceAdapter)


def test_build_pipeline_uses_real_lifecycle_when_url_present(
    fixed_clock, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("TRUTH_EXPIRY_USE_FAKES", raising=False)
    pipeline = build_pipeline(
        clock=fixed_clock,
        use_fakes=False,
        lifecycle_mcp_url="http://127.0.0.1:8000/mcp",
    )
    assert isinstance(pipeline._lifecycle, LifecycleMcpAdapter)


def test_build_pipeline_requires_mcp_url_when_fakes_disabled(no_fake_env: None):
    with pytest.raises(
        LiveAdaptersUnavailableError, match="TRUTH_EXPIRY_LIFECYCLE_MCP_URL"
    ):
        build_pipeline(use_fakes=False)
