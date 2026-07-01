from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from truthexpiry.demo.preflight import (
    EXIT_CONFIG,
    EXIT_HEALTH,
    EXIT_OK,
    EXIT_REPOSITORY,
    PROFILE_BACKUP_A,
    PROFILE_BACKUP_B,
    PROFILE_LIVE,
    CheckStatus,
    PreflightOptions,
    format_human_report,
    probe_http_status,
    render_report,
    run_preflight,
    validate_health_base,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]

_BOT = "SECRET-SLACK-BOT-9821"
_APP = "SECRET-SLACK-APP-4722"
_OPENAI = "SECRET-OPENAI-7718"
_MCP_AUTH = "SECRET-MCP-6643"
_URL_PASSWORD = "SECRET-URL-PASSWORD-5512"
_ALL_MARKERS = (_BOT, _APP, _OPENAI, _MCP_AUTH, _URL_PASSWORD)


def _live_env(**overrides: str) -> dict[str, str]:
    env = {
        "SLACK_BOT_TOKEN": _BOT,
        "SLACK_APP_TOKEN": _APP,
        "TRUTH_EXPIRY_LIFECYCLE_MCP_URL": "http://127.0.0.1:8000/mcp",
        "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN": _MCP_AUTH,
        "TRUTH_EXPIRY_CLAIM_EXTRACTOR": "live",
        "OPENAI_API_KEY": _OPENAI,
    }
    env.update(overrides)
    return env


def _backup_a_env(**overrides: str) -> dict[str, str]:
    env = {
        "SLACK_BOT_TOKEN": _BOT,
        "SLACK_APP_TOKEN": _APP,
        "TRUTH_EXPIRY_LIFECYCLE_MCP_URL": "http://127.0.0.1:8000/mcp",
        "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN": _MCP_AUTH,
        "TRUTH_EXPIRY_CLAIM_EXTRACTOR": "fake",
    }
    env.update(overrides)
    return env


def _healthy_probe(_url: str, _timeout: float) -> int:
    if _url.endswith("/readyz"):
        return 200
    if _url.endswith("/healthz"):
        return 200
    return None


def _probe_map(status_by_suffix: dict[str, int | None]):
    def probe(url: str, timeout: float) -> int | None:
        del timeout
        for suffix, code in status_by_suffix.items():
            if url.endswith(suffix):
                return code
        return None

    return probe


def _git_runner_factory(
    *,
    head: str = "abc1234",
    dirty: bool = False,
    expected: str = "fullhash",
    head_full: str = "fullhash",
) -> object:
    def runner(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        del cwd
        command = args[1:]
        if command == ["rev-parse", "--short", "HEAD"]:
            return subprocess.CompletedProcess(args, 0, head, "")
        if command == ["status", "--porcelain"]:
            stdout = " M file\n" if dirty else ""
            return subprocess.CompletedProcess(args, 0, stdout, "")
        if command[0:1] == ["rev-parse"]:
            ref = command[1]
            if ref == "v0.4.0":
                return subprocess.CompletedProcess(args, 0, expected, "")
            return subprocess.CompletedProcess(args, 0, head_full, "")
        return subprocess.CompletedProcess(args, 1, "", "error")

    return runner


def _options(
    profile: str,
    env: dict[str, str] | None = None,
    *,
    http_probe=_healthy_probe,
    git_runner=None,
    structural_runner=None,
    expected_ref: str | None = None,
    run_structural_checks: bool = True,
) -> PreflightOptions:
    return PreflightOptions(
        profile=profile,
        env=env or {},
        repo_root=_REPO_ROOT,
        http_probe=http_probe,
        git_runner=git_runner or _git_runner_factory(),
        structural_runner=structural_runner,
        expected_ref=expected_ref,
        run_structural_checks=run_structural_checks,
    )


def test_live_profile_succeeds_with_required_names():
    report = run_preflight(_options(PROFILE_LIVE, _live_env()))
    assert report.exit_code == EXIT_OK
    assert report.ready is True


def test_live_profile_rejects_missing_slack_bot_token():
    env = _live_env()
    del env["SLACK_BOT_TOKEN"]
    report = run_preflight(_options(PROFILE_LIVE, env))
    assert report.exit_code == EXIT_CONFIG


def test_live_profile_rejects_missing_slack_app_token():
    env = _live_env()
    del env["SLACK_APP_TOKEN"]
    report = run_preflight(_options(PROFILE_LIVE, env))
    assert report.exit_code == EXIT_CONFIG


def test_live_profile_rejects_missing_mcp_url():
    env = _live_env()
    del env["TRUTH_EXPIRY_LIFECYCLE_MCP_URL"]
    report = run_preflight(_options(PROFILE_LIVE, env))
    assert report.exit_code == EXIT_CONFIG


def test_live_profile_rejects_missing_mcp_auth_token():
    env = _live_env()
    del env["TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN"]
    report = run_preflight(_options(PROFILE_LIVE, env))
    assert report.exit_code == EXIT_CONFIG


def test_live_profile_rejects_missing_openai_key():
    env = _live_env()
    del env["OPENAI_API_KEY"]
    report = run_preflight(_options(PROFILE_LIVE, env))
    assert report.exit_code == EXIT_CONFIG


def test_live_profile_rejects_fake_extractor():
    report = run_preflight(
        _options(PROFILE_LIVE, _live_env(TRUTH_EXPIRY_CLAIM_EXTRACTOR="fake"))
    )
    assert report.exit_code == EXIT_CONFIG


def test_live_profile_rejects_all_fake_mode():
    report = run_preflight(
        _options(PROFILE_LIVE, _live_env(TRUTH_EXPIRY_USE_FAKES="1"))
    )
    assert report.exit_code == EXIT_CONFIG


def test_backup_a_requires_slack_and_mcp_settings():
    report = run_preflight(_options(PROFILE_BACKUP_A, _backup_a_env()))
    assert report.exit_code == EXIT_OK


def test_backup_a_requires_extractor_fake():
    report = run_preflight(
        _options(PROFILE_BACKUP_A, _backup_a_env(TRUTH_EXPIRY_CLAIM_EXTRACTOR="live"))
    )
    assert report.exit_code == EXIT_CONFIG


def test_backup_a_does_not_require_openai_key():
    env = _backup_a_env()
    assert "OPENAI_API_KEY" not in env
    report = run_preflight(_options(PROFILE_BACKUP_A, env))
    assert report.exit_code == EXIT_OK


def test_backup_b_requires_no_secrets():
    report = run_preflight(
        _options(
            PROFILE_BACKUP_B,
            {},
            run_structural_checks=False,
        )
    )
    assert report.exit_code == EXIT_OK


def test_blank_values_count_as_missing():
    report = run_preflight(_options(PROFILE_LIVE, _live_env(SLACK_BOT_TOKEN="   ")))
    assert report.exit_code == EXIT_CONFIG


def test_explicit_mapping_is_used_not_ambient_environment(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", _BOT)
    report = run_preflight(_options(PROFILE_LIVE, {}))
    assert report.exit_code == EXIT_CONFIG


def test_human_output_excludes_secret_markers():
    report = run_preflight(_options(PROFILE_LIVE, _live_env()))
    text = format_human_report(report).lower()
    for marker in _ALL_MARKERS:
        assert marker.lower() not in text


def test_json_output_excludes_secret_markers():
    report = run_preflight(_options(PROFILE_LIVE, _live_env()))
    text = render_report(report, json_output=True).lower()
    for marker in _ALL_MARKERS:
        assert marker.lower() not in text


def test_validate_health_base_rejects_credentials_without_echo():
    with pytest.raises(ValueError, match="credentials"):
        validate_health_base(f"http://user:{_URL_PASSWORD}@127.0.0.1:8080")
    # ensure the password marker is not raised as part of validation message
    try:
        validate_health_base(f"http://user:{_URL_PASSWORD}@127.0.0.1:8080")
    except ValueError as exc:
        assert _URL_PASSWORD not in str(exc)


def test_http_failure_output_excludes_raw_exception_text():
    def failing_probe(_url: str, _timeout: float) -> int | None:
        raise OSError(f"boom {_BOT}")

    report = run_preflight(
        _options(PROFILE_LIVE, _live_env(), http_probe=failing_probe)
    )
    text = format_human_report(report)
    assert _BOT not in text
    assert "boom" not in text
    assert report.exit_code == EXIT_HEALTH


def test_all_health_endpoints_healthy_passes():
    report = run_preflight(
        _options(PROFILE_LIVE, _live_env(), http_probe=_healthy_probe)
    )
    assert report.exit_code == EXIT_OK


def test_worker_readiness_503_returns_health_exit_code():
    probe = _probe_map(
        {
            "/healthz": 200,
            "/readyz": 503,
        }
    )

    def mapped_probe(url: str, timeout: float) -> int | None:
        if "8080" in url:
            return probe(url, timeout)
        return _healthy_probe(url, timeout)

    report = run_preflight(_options(PROFILE_LIVE, _live_env(), http_probe=mapped_probe))
    assert report.exit_code == EXIT_HEALTH
    ready = next(check for check in report.checks if check.name == "worker_readyz")
    assert ready.detail == "not_ready"


def test_mcp_readiness_503_returns_health_exit_code():
    probe = _probe_map(
        {
            "/healthz": 200,
            "/readyz": 503,
        }
    )

    def mapped_probe(url: str, timeout: float) -> int | None:
        if "8001" in url:
            return probe(url, timeout)
        return _healthy_probe(url, timeout)

    report = run_preflight(_options(PROFILE_LIVE, _live_env(), http_probe=mapped_probe))
    assert report.exit_code == EXIT_HEALTH


def test_connection_timeout_reports_safe_health_failure():
    report = run_preflight(
        _options(PROFILE_LIVE, _live_env(), http_probe=lambda _u, _t: None)
    )
    assert report.exit_code == EXIT_HEALTH
    worker = next(check for check in report.checks if check.name == "worker_healthz")
    assert worker.detail == "unavailable"


def test_backup_b_skips_network_checks():
    report = run_preflight(_options(PROFILE_BACKUP_B, {}, run_structural_checks=False))
    health_checks = [check for check in report.checks if check.category == "health"]
    assert all(check.status is CheckStatus.SKIP for check in health_checks)


def test_health_probe_does_not_send_authorization_header(monkeypatch):
    captured: dict[str, str | None] = {}

    class _Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    def fake_urlopen(request, timeout=0):
        del timeout
        captured["authorization"] = request.headers.get("Authorization")
        return _Response()

    monkeypatch.setattr("truthexpiry.demo.preflight.urlopen", fake_urlopen)
    assert probe_http_status("http://127.0.0.1:8001/healthz", 1.0) == 200
    assert captured["authorization"] is None


def test_dataset_records_present_passes():
    report = run_preflight(_options(PROFILE_BACKUP_B, {}, run_structural_checks=False))
    prod_482 = next(
        check for check in report.checks if check.name == "dataset_prod_482"
    )
    prod_511 = next(
        check for check in report.checks if check.name == "dataset_prod_511"
    )
    assert prod_482.status is CheckStatus.PASS
    assert prod_511.status is CheckStatus.PASS


def test_missing_prod_482_fails_repository_exit_code(tmp_path: Path):
    dataset = json.loads(
        (_REPO_ROOT / "lifecycle_mcp/data/lifecycle_records.json").read_text()
    )
    dataset["records"] = [
        record for record in dataset["records"] if record["record_id"] != "PROD-482"
    ]
    dataset_path = tmp_path / "lifecycle_records.json"
    dataset_path.write_text(json.dumps(dataset), encoding="utf-8")

    report = run_preflight(
        PreflightOptions(
            profile=PROFILE_BACKUP_B,
            env={},
            repo_root=_REPO_ROOT,
            dataset_path=dataset_path,
            git_runner=_git_runner_factory(),
            run_structural_checks=False,
        )
    )
    assert report.exit_code == EXIT_REPOSITORY


def test_missing_prod_511_fails_repository_exit_code(tmp_path: Path):
    dataset = json.loads(
        (_REPO_ROOT / "lifecycle_mcp/data/lifecycle_records.json").read_text()
    )
    dataset["records"] = [
        record for record in dataset["records"] if record["record_id"] != "PROD-511"
    ]
    dataset_path = tmp_path / "lifecycle_records.json"
    dataset_path.write_text(json.dumps(dataset), encoding="utf-8")

    report = run_preflight(
        PreflightOptions(
            profile=PROFILE_BACKUP_B,
            env={},
            repo_root=_REPO_ROOT,
            dataset_path=dataset_path,
            git_runner=_git_runner_factory(),
            run_structural_checks=False,
        )
    )
    assert report.exit_code == EXIT_REPOSITORY


def test_malformed_dataset_json_fails_safely(tmp_path: Path):
    dataset_path = tmp_path / "lifecycle_records.json"
    dataset_path.write_text("{not-json", encoding="utf-8")
    report = run_preflight(
        PreflightOptions(
            profile=PROFILE_BACKUP_B,
            env={},
            repo_root=_REPO_ROOT,
            dataset_path=dataset_path,
            git_runner=_git_runner_factory(),
            run_structural_checks=False,
        )
    )
    assert report.exit_code == EXIT_REPOSITORY
    text = format_human_report(report)
    assert "disabled" not in text


def test_missing_required_record_field_fails_without_record_dump(tmp_path: Path):
    dataset = json.loads(
        (_REPO_ROOT / "lifecycle_mcp/data/lifecycle_records.json").read_text()
    )
    for record in dataset["records"]:
        if record["record_id"] == "PROD-482":
            del record["value"]
    dataset_path = tmp_path / "lifecycle_records.json"
    dataset_path.write_text(json.dumps(dataset), encoding="utf-8")

    report = run_preflight(
        PreflightOptions(
            profile=PROFILE_BACKUP_B,
            env={},
            repo_root=_REPO_ROOT,
            dataset_path=dataset_path,
            git_runner=_git_runner_factory(),
            run_structural_checks=False,
        )
    )
    text = format_human_report(report)
    assert "disabled" not in text
    assert report.exit_code == EXIT_REPOSITORY


def test_expected_ref_match_passes():
    report = run_preflight(
        _options(
            PROFILE_BACKUP_B,
            {},
            expected_ref="v0.4.0",
            run_structural_checks=False,
        )
    )
    ref = next(check for check in report.checks if check.name == "git_expected_ref")
    assert ref.status is CheckStatus.PASS


def test_expected_ref_mismatch_returns_repository_exit_code():
    report = run_preflight(
        _options(
            PROFILE_BACKUP_B,
            {},
            expected_ref="v0.4.0",
            git_runner=_git_runner_factory(expected="other", head_full="different"),
            run_structural_checks=False,
        )
    )
    assert report.exit_code == EXIT_REPOSITORY


def test_dirty_worktree_is_reported():
    report = run_preflight(
        _options(
            PROFILE_BACKUP_B,
            {},
            git_runner=_git_runner_factory(dirty=True),
            run_structural_checks=False,
        )
    )
    worktree = next(check for check in report.checks if check.name == "git_worktree")
    assert worktree.detail == "dirty"
    assert report.exit_code == EXIT_REPOSITORY


def test_structural_check_success():
    def structural_runner(args, cwd, timeout, env):
        del cwd, timeout, env
        return subprocess.CompletedProcess(args, 0, "Configuration structure: OK\n", "")

    report = run_preflight(
        _options(
            PROFILE_BACKUP_B,
            {},
            structural_runner=structural_runner,
        )
    )
    worker = next(check for check in report.checks if check.name == "worker_structure")
    mcp = next(check for check in report.checks if check.name == "mcp_structure")
    assert worker.status is CheckStatus.PASS
    assert mcp.status is CheckStatus.PASS


def test_structural_timeout_fails_safely():
    def structural_runner(args, cwd, timeout, env):
        del args, cwd, timeout, env
        raise subprocess.TimeoutExpired(cmd="app.py", timeout=1)

    report = run_preflight(
        _options(
            PROFILE_BACKUP_B,
            {},
            structural_runner=structural_runner,
        )
    )
    worker = next(check for check in report.checks if check.name == "worker_structure")
    assert worker.detail == "timeout"
    text = format_human_report(report)
    assert "Configuration structure" not in text


def test_structural_failure_output_excludes_raw_subprocess_output():
    secret = "SECRET-STRUCTURAL-OUTPUT-9912"

    def structural_runner(args, cwd, timeout, env):
        del cwd, timeout, env
        return subprocess.CompletedProcess(args, 1, secret, secret)

    report = run_preflight(
        _options(
            PROFILE_BACKUP_B,
            {},
            structural_runner=structural_runner,
        )
    )
    text = format_human_report(report)
    assert secret not in text


def test_human_check_ordering_is_deterministic():
    report = run_preflight(_options(PROFILE_LIVE, _live_env()))
    category_order = {"configuration": 0, "health": 1, "repository": 2, "structural": 3}
    expected_names = [
        check.name
        for check in sorted(
            report.checks,
            key=lambda check: (category_order.get(check.category, 99), check.name),
        )
    ]
    assert [check.name for check in report.checks] == expected_names


def test_json_schema_is_stable():
    report = run_preflight(_options(PROFILE_BACKUP_B, {}, run_structural_checks=False))
    payload = json.loads(render_report(report, json_output=True))
    assert payload["status"] in {"ready", "not_ready"}
    assert payload["profile"] == PROFILE_BACKUP_B
    assert isinstance(payload["checks"], list)
    assert payload["exit_code"] == report.exit_code
    for check in payload["checks"]:
        assert set(check) <= {"name", "status", "category", "detail"}


def test_exit_code_precedence_configuration_over_health():
    report = run_preflight(
        _options(
            PROFILE_LIVE,
            _live_env(SLACK_BOT_TOKEN=""),
            http_probe=lambda _u, _t: None,
        )
    )
    assert report.exit_code == EXIT_CONFIG


def test_ready_output_does_not_claim_live_slack_success():
    report = run_preflight(_options(PROFILE_LIVE, _live_env()))
    text = format_human_report(report)
    assert "live Slack RTS" in text or "does not verify" in text


def test_output_names_selected_profile():
    report = run_preflight(_options(PROFILE_BACKUP_A, _backup_a_env()))
    text = format_human_report(report)
    assert "Profile: backup-a" in text


def test_backup_mode_is_not_mislabeled_as_live():
    report = run_preflight(_options(PROFILE_BACKUP_A, _backup_a_env()))
    payload = json.loads(render_report(report, json_output=True))
    assert payload["profile"] == PROFILE_BACKUP_A


def test_cli_backup_b_runs():
    import subprocess as sp

    dirty = sp.run(
        ["git", "status", "--porcelain"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if dirty.stdout.strip():
        pytest.skip("worktree is dirty")

    import scripts.demo_preflight as cli

    code = cli.main(
        [
            "--profile",
            PROFILE_BACKUP_B,
            "--repo-root",
            str(_REPO_ROOT),
            "--skip-structural",
        ]
    )
    assert code == EXIT_OK
