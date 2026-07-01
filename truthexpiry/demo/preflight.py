from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ProfileName = str

PROFILE_LIVE = "live"
PROFILE_BACKUP_A = "backup-a"
PROFILE_BACKUP_B = "backup-b"
VALID_PROFILES = frozenset({PROFILE_LIVE, PROFILE_BACKUP_A, PROFILE_BACKUP_B})

EXIT_OK = 0
EXIT_CONFIG = 1
EXIT_HEALTH = 2
EXIT_REPOSITORY = 3

STRUCTURAL_TIMEOUT_SECONDS = 30.0

_CHECK_ORDER = ("configuration", "health", "repository", "structural")

_DATASET_PATH = Path("lifecycle_mcp/data/lifecycle_records.json")
_REQUIRED_RECORD_FIELDS = (
    "record_id",
    "entity",
    "attribute",
    "scope",
    "value",
    "state",
    "effective_date",
)
_DEMO_RECORD_ASSERTIONS: dict[str, dict[str, str]] = {
    "PROD-482": {
        "entity": "report_export",
        "attribute": "availability",
        "value": "disabled",
    },
    "PROD-511": {
        "entity": "api_rate_limit",
        "attribute": "max_requests",
        "value": "50",
    },
}

_LIVE_ENV_NAMES = (
    "SLACK_BOT_TOKEN",
    "SLACK_APP_TOKEN",
    "TRUTH_EXPIRY_LIFECYCLE_MCP_URL",
    "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN",
    "TRUTH_EXPIRY_CLAIM_EXTRACTOR",
    "OPENAI_API_KEY",
)
_BACKUP_A_ENV_NAMES = (
    "SLACK_BOT_TOKEN",
    "SLACK_APP_TOKEN",
    "TRUTH_EXPIRY_LIFECYCLE_MCP_URL",
    "TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_TOKEN",
    "TRUTH_EXPIRY_CLAIM_EXTRACTOR",
)

HttpProbeFn = Callable[[str, float], int | None]


class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: CheckStatus
    category: str
    detail: str = ""

    def to_json(self) -> dict[str, str]:
        payload: dict[str, str] = {
            "name": self.name,
            "status": self.status.value,
            "category": self.category,
        }
        if self.detail:
            payload["detail"] = self.detail
        return payload


@dataclass
class PreflightReport:
    profile: str
    checks: list[CheckResult] = field(default_factory=list)
    exit_code: int = EXIT_OK

    @property
    def ready(self) -> bool:
        return self.exit_code == EXIT_OK

    def to_json(self) -> dict[str, Any]:
        return {
            "status": "ready" if self.ready else "not_ready",
            "profile": self.profile,
            "checks": [check.to_json() for check in self.checks],
            "exit_code": self.exit_code,
        }


@dataclass(frozen=True)
class PreflightOptions:
    profile: str
    json_output: bool = False
    expected_ref: str | None = None
    worker_health_base: str = "http://127.0.0.1:8080"
    mcp_health_base: str = "http://127.0.0.1:8001"
    timeout_seconds: float = 2.0
    repo_root: Path = field(default_factory=lambda: Path.cwd())
    env: Mapping[str, str] | None = None
    http_probe: HttpProbeFn | None = None
    git_runner: (
        Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None
    ) = None
    structural_runner: (
        Callable[
            [Sequence[str], Path, float, Mapping[str, str]],
            subprocess.CompletedProcess[str],
        ]
        | None
    ) = None
    run_structural_checks: bool = True
    dataset_path: Path | None = None


def _env_map(options: PreflightOptions) -> Mapping[str, str]:
    return os.environ if options.env is None else options.env


def _is_present(env: Mapping[str, str], name: str) -> bool:
    value = env.get(name)
    return value is not None and bool(value.strip())


def _parse_bool_env(env: Mapping[str, str], name: str, default: bool = False) -> bool:
    raw = env.get(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def validate_health_base(base: str) -> str:
    parsed = urlparse(base.strip().rstrip("/"))
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("health base must use http or https")
    if parsed.username or parsed.password:
        raise ValueError("health base must not contain credentials")
    if not parsed.hostname:
        raise ValueError("health base must include a host")
    port_suffix = f":{parsed.port}" if parsed.port else ""
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{host}{port_suffix}{path}"


def probe_http_status(url: str, timeout_seconds: float) -> int | None:
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            return int(response.status)
    except HTTPError as exc:
        return int(exc.code)
    except (URLError, TimeoutError, OSError, ValueError):
        return None


def _probe_endpoint(
    *,
    options: PreflightOptions,
    base: str,
    path: str,
) -> int | None:
    normalized_base = validate_health_base(base)
    url = f"{normalized_base}{path}"
    probe = options.http_probe or probe_http_status
    try:
        return probe(url, options.timeout_seconds)
    except Exception:
        return None


def _check_environment(profile: str, env: Mapping[str, str]) -> list[CheckResult]:
    checks: list[CheckResult] = []

    if profile == PROFILE_BACKUP_B:
        checks.append(
            CheckResult(
                name="environment_secrets",
                status=CheckStatus.PASS,
                category="configuration",
                detail="not_required",
            )
        )
        return checks

    required_names = _LIVE_ENV_NAMES if profile == PROFILE_LIVE else _BACKUP_A_ENV_NAMES
    missing = [name for name in required_names if not _is_present(env, name)]
    if missing:
        checks.append(
            CheckResult(
                name="required_environment_names",
                status=CheckStatus.FAIL,
                category="configuration",
                detail=f"missing:{','.join(missing)}",
            )
        )
    else:
        checks.append(
            CheckResult(
                name="required_environment_names",
                status=CheckStatus.PASS,
                category="configuration",
                detail="present",
            )
        )

    use_fakes = _parse_bool_env(env, "TRUTH_EXPIRY_USE_FAKES", default=False)
    if use_fakes:
        checks.append(
            CheckResult(
                name="use_fakes_disabled",
                status=CheckStatus.FAIL,
                category="configuration",
                detail="invalid",
            )
        )
    else:
        checks.append(
            CheckResult(
                name="use_fakes_disabled",
                status=CheckStatus.PASS,
                category="configuration",
                detail="ok",
            )
        )

    extractor = env.get("TRUTH_EXPIRY_CLAIM_EXTRACTOR", "").strip().lower()
    if profile == PROFILE_LIVE:
        if extractor != "live":
            checks.append(
                CheckResult(
                    name="claim_extractor_live",
                    status=CheckStatus.FAIL,
                    category="configuration",
                    detail="invalid",
                )
            )
        else:
            checks.append(
                CheckResult(
                    name="claim_extractor_live",
                    status=CheckStatus.PASS,
                    category="configuration",
                    detail="ok",
                )
            )
    else:
        if extractor != "fake":
            checks.append(
                CheckResult(
                    name="claim_extractor_fake",
                    status=CheckStatus.FAIL,
                    category="configuration",
                    detail="invalid",
                )
            )
        else:
            checks.append(
                CheckResult(
                    name="claim_extractor_fake",
                    status=CheckStatus.PASS,
                    category="configuration",
                    detail="ok",
                )
            )

    if profile == PROFILE_BACKUP_A:
        if _is_present(env, "OPENAI_API_KEY"):
            checks.append(
                CheckResult(
                    name="openai_not_required",
                    status=CheckStatus.PASS,
                    category="configuration",
                    detail="present_optional",
                )
            )
        else:
            checks.append(
                CheckResult(
                    name="openai_not_required",
                    status=CheckStatus.PASS,
                    category="configuration",
                    detail="not_required",
                )
            )

    return checks


def _health_check_result(
    *,
    service: str,
    endpoint: str,
    status_code: int | None,
    require_ready: bool,
) -> CheckResult:
    name = f"{service}_{endpoint}"
    category = "health"
    if status_code is None:
        return CheckResult(
            name=name,
            status=CheckStatus.FAIL,
            category=category,
            detail="unavailable",
        )
    if endpoint == "healthz":
        if status_code == 200:
            return CheckResult(
                name=name,
                status=CheckStatus.PASS,
                category=category,
                detail="ok",
            )
        return CheckResult(
            name=name,
            status=CheckStatus.FAIL,
            category=category,
            detail=f"http_{status_code}",
        )
    if status_code == 200:
        return CheckResult(
            name=name,
            status=CheckStatus.PASS,
            category=category,
            detail="ok",
        )
    if status_code == 503:
        return CheckResult(
            name=name,
            status=CheckStatus.FAIL,
            category=category,
            detail="not_ready",
        )
    return CheckResult(
        name=name,
        status=CheckStatus.FAIL,
        category=category,
        detail=f"http_{status_code}",
    )


def _check_health(options: PreflightOptions) -> list[CheckResult]:
    if options.profile == PROFILE_BACKUP_B:
        return [
            CheckResult(
                name="worker_healthz",
                status=CheckStatus.SKIP,
                category="health",
            ),
            CheckResult(
                name="worker_readyz",
                status=CheckStatus.SKIP,
                category="health",
            ),
            CheckResult(
                name="mcp_healthz",
                status=CheckStatus.SKIP,
                category="health",
            ),
            CheckResult(
                name="mcp_readyz",
                status=CheckStatus.SKIP,
                category="health",
            ),
        ]

    checks: list[CheckResult] = []
    worker_health = _probe_endpoint(
        options=options, base=options.worker_health_base, path="/healthz"
    )
    checks.append(
        _health_check_result(
            service="worker",
            endpoint="healthz",
            status_code=worker_health,
            require_ready=False,
        )
    )
    worker_ready = _probe_endpoint(
        options=options, base=options.worker_health_base, path="/readyz"
    )
    checks.append(
        _health_check_result(
            service="worker",
            endpoint="readyz",
            status_code=worker_ready,
            require_ready=True,
        )
    )
    mcp_health = _probe_endpoint(
        options=options, base=options.mcp_health_base, path="/healthz"
    )
    checks.append(
        _health_check_result(
            service="mcp",
            endpoint="healthz",
            status_code=mcp_health,
            require_ready=False,
        )
    )
    mcp_ready = _probe_endpoint(
        options=options, base=options.mcp_health_base, path="/readyz"
    )
    checks.append(
        _health_check_result(
            service="mcp",
            endpoint="readyz",
            status_code=mcp_ready,
            require_ready=True,
        )
    )
    return checks


def _load_dataset(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("dataset root must be an object")
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("dataset records must be a list")
    return payload


def _check_dataset(
    repo_root: Path, dataset_path: Path | None = None
) -> list[CheckResult]:
    path = dataset_path or (repo_root / _DATASET_PATH)
    checks: list[CheckResult] = []

    if not path.is_file():
        checks.append(
            CheckResult(
                name="dataset_file",
                status=CheckStatus.FAIL,
                category="repository",
                detail="missing",
            )
        )
        return checks

    try:
        payload = _load_dataset(path)
    except (OSError, json.JSONDecodeError, ValueError):
        checks.append(
            CheckResult(
                name="dataset_file",
                status=CheckStatus.FAIL,
                category="repository",
                detail="invalid",
            )
        )
        return checks

    checks.append(
        CheckResult(
            name="dataset_file",
            status=CheckStatus.PASS,
            category="repository",
            detail="ok",
        )
    )

    records_by_id: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(payload["records"]):
        if not isinstance(record, dict):
            checks.append(
                CheckResult(
                    name="dataset_record_shape",
                    status=CheckStatus.FAIL,
                    category="repository",
                    detail=f"index_{index}",
                )
            )
            return checks
        record_id = record.get("record_id")
        if not isinstance(record_id, str) or not record_id:
            checks.append(
                CheckResult(
                    name="dataset_record_id",
                    status=CheckStatus.FAIL,
                    category="repository",
                    detail=f"index_{index}",
                )
            )
            return checks
        records_by_id[record_id] = record

    for record_id, expected_fields in _DEMO_RECORD_ASSERTIONS.items():
        name = f"dataset_{record_id.lower().replace('-', '_')}"
        record = records_by_id.get(record_id)
        if record is None:
            checks.append(
                CheckResult(
                    name=name,
                    status=CheckStatus.FAIL,
                    category="repository",
                    detail="missing",
                )
            )
            continue
        missing_field = next(
            (
                field_name
                for field_name in _REQUIRED_RECORD_FIELDS
                if field_name not in record
            ),
            None,
        )
        if missing_field is not None:
            checks.append(
                CheckResult(
                    name=name,
                    status=CheckStatus.FAIL,
                    category="repository",
                    detail=f"missing_field:{missing_field}",
                )
            )
            continue
        mismatch = next(
            (
                field_name
                for field_name, expected_value in expected_fields.items()
                if str(record.get(field_name)) != expected_value
            ),
            None,
        )
        if mismatch is not None:
            checks.append(
                CheckResult(
                    name=name,
                    status=CheckStatus.FAIL,
                    category="repository",
                    detail=f"unexpected_field:{mismatch}",
                )
            )
            continue
        checks.append(
            CheckResult(
                name=name,
                status=CheckStatus.PASS,
                category="repository",
                detail="present",
            )
        )

    return checks


def _default_git_runner(
    args: Sequence[str], cwd: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _check_git(options: PreflightOptions) -> list[CheckResult]:
    runner = options.git_runner or _default_git_runner
    checks: list[CheckResult] = []

    head = runner(["git", "rev-parse", "--short", "HEAD"], options.repo_root)
    if head.returncode != 0:
        checks.append(
            CheckResult(
                name="git_commit",
                status=CheckStatus.FAIL,
                category="repository",
                detail="unavailable",
            )
        )
    else:
        commit = head.stdout.strip()
        checks.append(
            CheckResult(
                name="git_commit",
                status=CheckStatus.PASS,
                category="repository",
                detail=commit,
            )
        )

    status = runner(["git", "status", "--porcelain"], options.repo_root)
    if status.returncode != 0:
        checks.append(
            CheckResult(
                name="git_worktree",
                status=CheckStatus.FAIL,
                category="repository",
                detail="unavailable",
            )
        )
    elif status.stdout.strip():
        checks.append(
            CheckResult(
                name="git_worktree",
                status=CheckStatus.FAIL,
                category="repository",
                detail="dirty",
            )
        )
    else:
        checks.append(
            CheckResult(
                name="git_worktree",
                status=CheckStatus.PASS,
                category="repository",
                detail="clean",
            )
        )

    if options.expected_ref:
        expected = runner(
            ["git", "rev-parse", options.expected_ref],
            options.repo_root,
        )
        current = runner(["git", "rev-parse", "HEAD"], options.repo_root)
        if expected.returncode != 0 or current.returncode != 0:
            checks.append(
                CheckResult(
                    name="git_expected_ref",
                    status=CheckStatus.FAIL,
                    category="repository",
                    detail="unavailable",
                )
            )
        elif expected.stdout.strip() != current.stdout.strip():
            checks.append(
                CheckResult(
                    name="git_expected_ref",
                    status=CheckStatus.FAIL,
                    category="repository",
                    detail="mismatch",
                )
            )
        else:
            checks.append(
                CheckResult(
                    name="git_expected_ref",
                    status=CheckStatus.PASS,
                    category="repository",
                    detail="match",
                )
            )

    return checks


def _default_structural_runner(
    args: Sequence[str],
    cwd: Path,
    timeout_seconds: float,
    env: Mapping[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
        env=dict(env),
    )


def _check_repository_layout(repo_root: Path) -> list[CheckResult]:
    checks: list[CheckResult] = []
    for relative, name in (
        ("app.py", "app_entrypoint"),
        ("lifecycle_mcp/server.py", "mcp_entrypoint"),
    ):
        path = repo_root / relative
        if path.is_file():
            checks.append(
                CheckResult(
                    name=name,
                    status=CheckStatus.PASS,
                    category="repository",
                    detail="present",
                )
            )
        else:
            checks.append(
                CheckResult(
                    name=name,
                    status=CheckStatus.FAIL,
                    category="repository",
                    detail="missing",
                )
            )
    return checks


def _check_structural(options: PreflightOptions) -> list[CheckResult]:
    if not options.run_structural_checks or options.profile != PROFILE_BACKUP_B:
        return [
            CheckResult(
                name="worker_structure",
                status=CheckStatus.SKIP,
                category="structural",
            ),
            CheckResult(
                name="mcp_structure",
                status=CheckStatus.SKIP,
                category="structural",
            ),
        ]

    runner = options.structural_runner or _default_structural_runner
    checks: list[CheckResult] = []
    structural_env = dict(os.environ)
    structural_env["TRUTH_EXPIRY_LIFECYCLE_MCP_AUTH_DISABLED"] = "1"

    for name, args in (
        ("worker_structure", [sys.executable, "app.py", "--check"]),
        ("mcp_structure", [sys.executable, "-m", "lifecycle_mcp.server", "--check"]),
    ):
        try:
            result = runner(
                args,
                options.repo_root,
                STRUCTURAL_TIMEOUT_SECONDS,
                structural_env,
            )
        except subprocess.TimeoutExpired:
            checks.append(
                CheckResult(
                    name=name,
                    status=CheckStatus.FAIL,
                    category="structural",
                    detail="timeout",
                )
            )
            continue
        if result.returncode == 0:
            checks.append(
                CheckResult(
                    name=name,
                    status=CheckStatus.PASS,
                    category="structural",
                    detail="ok",
                )
            )
        else:
            checks.append(
                CheckResult(
                    name=name,
                    status=CheckStatus.FAIL,
                    category="structural",
                    detail="failed",
                )
            )
    return checks


def _compute_exit_code(checks: Sequence[CheckResult]) -> int:
    failed_categories = {
        check.category for check in checks if check.status is CheckStatus.FAIL
    }
    if "configuration" in failed_categories:
        return EXIT_CONFIG
    if "health" in failed_categories:
        return EXIT_HEALTH
    if failed_categories & {"repository", "structural"}:
        return EXIT_REPOSITORY
    return EXIT_OK


def _sort_checks(checks: Sequence[CheckResult]) -> list[CheckResult]:
    category_order = {name: index for index, name in enumerate(_CHECK_ORDER)}
    return sorted(
        checks,
        key=lambda check: (category_order.get(check.category, 99), check.name),
    )


def run_preflight(options: PreflightOptions) -> PreflightReport:
    if options.profile not in VALID_PROFILES:
        raise ValueError(f"unsupported profile: {options.profile}")

    env = _env_map(options)
    checks: list[CheckResult] = []
    checks.extend(_check_environment(options.profile, env))
    checks.extend(_check_health(options))
    checks.extend(_check_repository_layout(options.repo_root))
    checks.extend(_check_dataset(options.repo_root, options.dataset_path))
    checks.extend(_check_git(options))
    checks.extend(_check_structural(options))

    ordered = _sort_checks(checks)
    exit_code = _compute_exit_code(ordered)
    return PreflightReport(profile=options.profile, checks=ordered, exit_code=exit_code)


def format_human_report(report: PreflightReport) -> str:
    lines = ["TruthExpiry demo preflight", f"Profile: {report.profile}", ""]
    for check in report.checks:
        if check.status is CheckStatus.SKIP:
            marker = "SKIP"
        elif check.status is CheckStatus.PASS:
            marker = "PASS"
        else:
            marker = "FAIL"
        suffix = f" ({check.detail})" if check.detail else ""
        lines.append(f"[{marker}] {check.name}{suffix}")
    lines.append("")
    if report.ready:
        lines.append("READY TO RECORD")
        lines.append(
            "Infrastructure and configuration checks passed. "
            "This does not verify live Slack RTS or OpenAI extraction."
        )
    else:
        lines.append("NOT READY")
    return "\n".join(lines)


def render_report(report: PreflightReport, *, json_output: bool) -> str:
    if json_output:
        return json.dumps(report.to_json(), indent=2, sort_keys=True)
    return format_human_report(report)
