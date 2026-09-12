"""The capability contract.

Shapes only. Validation belongs to the broker at ingress (AR-16), policy evaluation to the
policy engine (AR-3), and canonical id derivation to the broker (AR-15) -- none of which
exist yet. Nothing here may acquire the ability to execute anything.

Specified in docs/design/02-capability-model.md.
"""

from __future__ import annotations

import dataclasses
from enum import StrEnum
from typing import Any

SCHEMA_VERSION = 1


class Provenance(StrEnum):
    """Whether the context that formed this request had handled untrusted input (AR-11)."""

    TRUSTED = "trusted"
    DERIVED_FROM_UNTRUSTED = "derived_from_untrusted"


class Outcome(StrEnum):
    """Deliberately not collapsed into SUCCESS/FAILURE; see docs/design/02."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    DENIED = "DENIED"
    """Policy said no. A decision, not a malfunction."""
    REJECTED = "REJECTED"
    """Failed schema validation at ingress. A bug in the caller."""
    DUPLICATE = "DUPLICATE"
    """Already executed. Prior result returned; nothing new happened."""
    TIMEOUT = "TIMEOUT"
    ABORTED_COST = "ABORTED_COST"
    """Hit a cost ceiling. A policy event worth counting separately."""
    UNKNOWN = "UNKNOWN"
    """The side effect may or may not have occurred.

    Reached when execution began but the outcome could not be durably established -- most
    often a failed AUDIT CLOSE after a successful provider call. Never resolve this to
    FAILURE: a retry would then duplicate a side effect that already happened (AR-4).
    """


TERMINAL_OUTCOMES = frozenset(
    {
        Outcome.SUCCESS,
        Outcome.FAILURE,
        Outcome.DENIED,
        Outcome.REJECTED,
        Outcome.DUPLICATE,
        Outcome.TIMEOUT,
        Outcome.ABORTED_COST,
    }
)
"""UNKNOWN is absent by design: it holds a request out of both paths until reconciliation."""


@dataclasses.dataclass(frozen=True, slots=True)
class Cost:
    usd: float = 0.0
    tokens: int = 0
    duration_ms: int = 0

    def as_json(self) -> dict[str, Any]:
        return {"usd": self.usd, "tokens": self.tokens, "duration_ms": self.duration_ms}


@dataclasses.dataclass(frozen=True, slots=True)
class CapabilityRequest:
    """An inert proposal. Carries no authority and cannot execute anything.

    There is no caller-supplied request id. The broker derives the canonical id from
    idempotency_key plus request content, so a caller cannot vary an opaque field to evade
    deduplication (AR-15).
    """

    idempotency_key: str
    """Identifies the logical operation *instance*.

    Stable across retries of one intent, distinct across separate intents. Cycle number at
    0.0. The content hash added by the broker guards against mutation within the instance --
    the two do different jobs, and collapsing them into pure content addressing would make
    a legitimately repeated action look like a duplicate.
    """

    actor: str
    capability: str
    """A declared capability id. Never a free-form provider call (AR-16)."""

    target: str
    parameters: dict[str, Any] = dataclasses.field(default_factory=dict)
    estimated_cost: Cost = dataclasses.field(default_factory=Cost)
    justification: str = ""
    decision_ref: str | None = None
    provenance: Provenance = Provenance.TRUSTED
    schema_version: int = SCHEMA_VERSION

    def as_json(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "idempotency_key": self.idempotency_key,
            "actor": self.actor,
            "capability": self.capability,
            "target": self.target,
            "parameters": self.parameters,
            "estimated_cost": self.estimated_cost.as_json(),
            "justification": self.justification,
            "decision_ref": self.decision_ref,
            "provenance": str(self.provenance),
        }


@dataclasses.dataclass(frozen=True, slots=True)
class CapabilityResult:
    outcome: Outcome
    canonical_id: str
    actual_cost: Cost = dataclasses.field(default_factory=Cost)
    artifacts: tuple[str, ...] = ()
    """References, never inline contents -- so a large result cannot flood model context."""

    audit_id: str | None = None
    error: dict[str, Any] | None = None
    rule: str | None = None
    """For DENIED, the rule that decided it. 'DENY' alone is not actionable."""

    @property
    def is_terminal(self) -> bool:
        return self.outcome in TERMINAL_OUTCOMES

    def as_json(self) -> dict[str, Any]:
        return {
            "outcome": str(self.outcome),
            "canonical_id": self.canonical_id,
            "actual_cost": self.actual_cost.as_json(),
            "artifacts": list(self.artifacts),
            "audit_id": self.audit_id,
            "error": self.error,
            "rule": self.rule,
        }
