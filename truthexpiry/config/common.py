from __future__ import annotations

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


class ConfigError(ValueError):
    """Configuration error that names variables but never their values."""

    def __init__(self, message: str) -> None:
        super().__init__(message)

    def __repr__(self) -> str:
        return f"ConfigError({self.args[0]!r})"


@dataclass(frozen=True)
class SecretValue:
    """In-memory secret wrapper with redacted string forms."""

    _value: str

    @classmethod
    def from_optional(cls, value: str | None) -> "SecretValue | None":
        if value is None:
            return None
        return cls(value)

    def get_secret(self) -> str:
        return self._value

    def __str__(self) -> str:
        return "SecretValue('********')"

    def __repr__(self) -> str:
        return "SecretValue('********')"


def _env_map(env: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if env is None else env


def get_optional_non_blank(
    env: Mapping[str, str] | None,
    name: str,
    *,
    default: str | None = None,
) -> str | None:
    mapping = _env_map(env)
    if name not in mapping:
        return default
    value = mapping[name].strip()
    if not value:
        return None
    return value


def require_non_blank(env: Mapping[str, str] | None, name: str) -> str:
    value = get_optional_non_blank(env, name)
    if value is None:
        raise ConfigError(f"{name} is required")
    return value


def parse_bool(
    env: Mapping[str, str] | None,
    name: str,
    *,
    default: bool,
) -> bool:
    mapping = _env_map(env)
    if name not in mapping:
        return default
    raw = mapping[name].strip().lower()
    if not raw:
        return default
    if raw in _TRUE_VALUES:
        return True
    if raw in _FALSE_VALUES:
        return False
    raise ConfigError(f"{name} must be a boolean value")


def parse_int(
    env: Mapping[str, str] | None,
    name: str,
    *,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    mapping = _env_map(env)
    if name not in mapping:
        value = default
    else:
        raw = mapping[name].strip()
        if not raw:
            value = default
        else:
            try:
                value = int(raw)
            except ValueError as exc:
                raise ConfigError(f"{name} must be an integer") from exc
    if minimum is not None and value < minimum:
        raise ConfigError(f"{name} must be an integer between {minimum} and {maximum}")
    if maximum is not None and value > maximum:
        raise ConfigError(f"{name} must be an integer between {minimum} and {maximum}")
    return value


def parse_float(
    env: Mapping[str, str] | None,
    name: str,
    *,
    default: float,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    mapping = _env_map(env)
    if name not in mapping:
        value = default
    else:
        raw = mapping[name].strip()
        if not raw:
            value = default
        else:
            try:
                value = float(raw)
            except ValueError as exc:
                raise ConfigError(f"{name} must be a number") from exc
    if not math.isfinite(value):
        raise ConfigError(f"{name} must be a finite number")
    if minimum is not None and value < minimum:
        raise ConfigError(f"{name} must be greater than {minimum}")
    if maximum is not None and value > maximum:
        raise ConfigError(f"{name} must be at most {maximum}")
    return value


def parse_port(env: Mapping[str, str] | None, name: str, *, default: int) -> int:
    return parse_int(env, name, default=default, minimum=1, maximum=65535)


def parse_choice(
    env: Mapping[str, str] | None,
    name: str,
    *,
    choices: frozenset[str],
    default: str | None = None,
    required: bool = False,
) -> str | None:
    mapping = _env_map(env)
    if name not in mapping:
        if required:
            raise ConfigError(f"{name} is required")
        return default
    raw = mapping[name].strip().lower()
    if not raw:
        if required:
            raise ConfigError(f"{name} is required")
        return default
    if raw not in choices:
        allowed = ", ".join(sorted(choices))
        raise ConfigError(f"{name} must be one of: {allowed}")
    return raw
