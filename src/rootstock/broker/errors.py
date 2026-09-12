"""Broker failures that are part of the protocol, not programming mistakes."""

from __future__ import annotations

from typing import Any


class IngressError(Exception):
    """Request is unroutable. Never reaches policy (AR-16)."""

    def __init__(self, rule: str, message: str) -> None:
        super().__init__(message)
        self.rule = rule
        self.message = message


class AuditWriteError(Exception):
    """Durable audit write failed."""


class ExecuteError(Exception):
    """Provider call began; outcome may be unknown."""

    def __init__(self, message: str, *, side_effect_likely: bool = True) -> None:
        super().__init__(message)
        self.side_effect_likely = side_effect_likely


def error_body(code: str, detail: str, **extra: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "detail": detail}
    body.update(extra)
    return body
