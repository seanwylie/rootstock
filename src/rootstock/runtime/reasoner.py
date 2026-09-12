"""The propose/execute boundary, from the propose side.

This interface is the load-bearing artifact of Phase 0. Phase 6 replaces StubReasoner with
ModelReasoner, and that swap is required to touch nothing outside a reasoner adapter --
if it does, the boundary leaked and that is a design finding rather than a merge conflict.

A Reasoner returns a Proposal. It cannot execute, cannot hold a credential, and cannot
observe anything it was not handed.
"""

from __future__ import annotations

import dataclasses
import itertools
from collections.abc import Iterator, Sequence
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from rootstock.shared import vocabulary
from rootstock.shared.capability import CapabilityRequest, Cost, Provenance


@dataclasses.dataclass(frozen=True, slots=True)
class LastCycle:
    number: int
    decision: str
    outcome: str
    timestamp: str
    expected_outcome_met: bool | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class Observation:
    """Everything the reasoner is permitted to see.

    Deterministic facts only. No free text from anywhere, no external content, and no prior
    model reasoning -- if chain-of-thought is not an audit log, it is not an input either.
    At 0.0 this is a closed epistemic system: Rootstock can learn about itself and nothing
    else. Web research opens it at 0.1, which is where AR-11 gets its first real workout.
    """

    cycle_number: int
    constitution_version: str
    capabilities_granted: tuple[str, ...]
    last_cycle: LastCycle | None = None
    consecutive_failures: int = 0
    sandbox_inventory: tuple[dict[str, Any], ...] = ()
    memory_summary: tuple[dict[str, Any], ...] = ()
    cost_to_date: dict[str, float] = dataclasses.field(default_factory=dict)
    pending_approvals: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class Proposal:
    """One proposed action, or the reasoning behind proposing none.

    expected_outcome is mandatory and must be checkable by the *next* cycle. It is what makes
    the loop a learning loop rather than immediate self-confirmation.
    """

    capability: str
    target: str
    parameters: dict[str, Any]
    estimated_cost: Cost
    justification: str
    expected_outcome: str
    alternatives: tuple[str, ...] = ()
    rationale: str = ""
    provenance: Provenance = Provenance.TRUSTED

    def to_request(
        self, *, actor: str, idempotency_key: str, decision_ref: str
    ) -> CapabilityRequest:
        return CapabilityRequest(
            idempotency_key=idempotency_key,
            actor=actor,
            capability=self.capability,
            target=self.target,
            parameters=dict(self.parameters),
            estimated_cost=self.estimated_cost,
            justification=self.justification,
            decision_ref=decision_ref,
            provenance=self.provenance,
        )


@runtime_checkable
class Reasoner(Protocol):
    """Proposes at most one action per cycle.

    Returning None is a valid and healthy outcome. A do-nothing cycle still produces a
    decision record.
    """

    def propose(self, observation: Observation) -> Proposal | None: ...


class StubMode(StrEnum):
    """Deterministic behaviours for exercising the pipeline without a model.

    A stub that only ever behaves well tests only the happy path, so the misbehaving modes
    are as important as NORMAL -- they are how D5 and D6 get driven through the real runtime
    rather than only through fixtures.
    """

    NORMAL = "normal"
    """A well-formed, in-scope, grantable request."""

    NOOP = "noop"
    """Propose nothing. Exercises do-nothing cycles."""

    MALFORMED = "malformed"
    """Violates the capability's parameter schema. Expect REJECTED at ingress."""

    UNDECLARED = "undeclared"
    """Names a capability id outside the vocabulary. Expect REJECTED, unroutable (D5)."""

    OUT_OF_SCOPE = "out_of_scope"
    """Well-formed, but targets a resource outside the granted scope. Expect DENIED (D6)."""

    UNTRUSTED_PROVENANCE = "untrusted_provenance"
    """Well-formed but marked derived_from_untrusted. Exercises the AR-11 restricted path."""


class StubReasoner:
    """A deterministic Reasoner with no model dependency.

    Holds no credentials, opens no sockets, reads no secrets. Given the same script and the
    same observations it produces the same proposals, which is what lets a pipeline failure
    be attributed to the pipeline.
    """

    def __init__(
        self, script: Sequence[StubMode] | StubMode = StubMode.NORMAL, *, repeat: bool = True
    ) -> None:
        modes = [script] if isinstance(script, StubMode) else list(script)
        if not modes:
            raise ValueError("script must contain at least one mode")
        self._modes = tuple(modes)
        self._sequence: Iterator[StubMode] = (
            itertools.cycle(self._modes) if repeat else iter(self._modes)
        )
        self.calls: list[Observation] = []

    @property
    def modes(self) -> tuple[StubMode, ...]:
        return self._modes

    def propose(self, observation: Observation) -> Proposal | None:
        self.calls.append(observation)
        try:
            mode = next(self._sequence)
        except StopIteration:
            return None
        return self._build(mode, observation)

    def _build(self, mode: StubMode, observation: Observation) -> Proposal | None:
        suffix = f"cycle-{observation.cycle_number}"

        match mode:
            case StubMode.NOOP:
                return None

            case StubMode.NORMAL | StubMode.UNTRUSTED_PROVENANCE:
                provenance = (
                    Provenance.DERIVED_FROM_UNTRUSTED
                    if mode is StubMode.UNTRUSTED_PROVENANCE
                    else Provenance.TRUSTED
                )
                return Proposal(
                    capability=vocabulary.SANDBOX_S3_CREATE_BUCKET,
                    target=f"{vocabulary.SANDBOX_BUCKET_PREFIX}{suffix}",
                    parameters={"suffix": suffix, "purpose": "cycle-artifact"},
                    estimated_cost=Cost(usd=0.0, tokens=0),
                    justification="Stub: create a bucket to hold this cycle's artifacts.",
                    expected_outcome=(
                        f"bucket {vocabulary.SANDBOX_BUCKET_PREFIX}{suffix} exists, "
                        "is tagged, and appears in inventory next cycle"
                    ),
                    alternatives=("do nothing", "write the summary to memory instead"),
                    rationale="Deterministic stub proposal; no model involved.",
                    provenance=provenance,
                )

            case StubMode.MALFORMED:
                return Proposal(
                    capability=vocabulary.SANDBOX_S3_CREATE_BUCKET,
                    # Uppercase and underscores violate the declared suffix pattern.
                    parameters={"suffix": "INVALID_Suffix!!"},
                    target=f"{vocabulary.SANDBOX_BUCKET_PREFIX}invalid",
                    estimated_cost=Cost(),
                    justification="Stub: deliberately malformed parameters.",
                    expected_outcome="rejected at ingress before policy evaluation",
                )

            case StubMode.UNDECLARED:
                return Proposal(
                    capability="aws.call",
                    target="s3",
                    parameters={"operation": "CreateBucket", "params": {"Bucket": "anything"}},
                    estimated_cost=Cost(),
                    justification="Stub: the generic-proxy shape AR-16 forbids.",
                    expected_outcome="unroutable at ingress; no such capability exists",
                )

            case StubMode.OUT_OF_SCOPE:
                return Proposal(
                    capability=vocabulary.SANDBOX_S3_PUT_OBJECT,
                    target="someone-elses-bucket",
                    parameters={"bucket": "someone-elses-bucket", "key": "x", "body": "x"},
                    estimated_cost=Cost(),
                    justification="Stub: targets a bucket outside the granted scope.",
                    expected_outcome="denied by scope rule, naming the rule",
                )

        raise AssertionError(f"unhandled stub mode: {mode}")
