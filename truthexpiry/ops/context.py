from __future__ import annotations

import contextvars
import uuid

correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "truthexpiry_correlation_id",
    default=None,
)


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def set_correlation_id(value: str) -> contextvars.Token[str | None]:
    return correlation_id_var.set(value)


def reset_correlation_id(token: contextvars.Token[str | None]) -> None:
    correlation_id_var.reset(token)


def get_correlation_id() -> str | None:
    return correlation_id_var.get()
