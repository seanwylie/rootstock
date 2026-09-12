"""Destructive-test registry and runner.

D1-D8 are defined in docs/design/01-rootstock-v0.md. Each deliberately breaks something and
asserts the system fails in the *correct direction* -- these are negative-space properties,
things that must remain impossible when components fail, and they are worth more than any
quantity of happy-path tests.

Structure is break / assert / restore. Restore is mandatory and runs even when the assertion
fails, because a harness that leaves a control disabled after a failed run is worse than no
harness.

Phase 5 fills the bodies. Factories are lazy so collecting the registry does not talk to AWS.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from enum import StrEnum
from typing import Protocol


class Phase(StrEnum):
    """The plan phase in which each test becomes runnable."""

    PHASE_2 = "phase-2"
    PHASE_3 = "phase-3"
    PHASE_4 = "phase-4"


class DestructiveTest(Protocol):
    def break_it(self) -> None: ...
    def assert_correct_failure(self) -> None: ...
    def restore(self) -> None: ...


@dataclasses.dataclass(frozen=True, slots=True)
class TestSpec:
    id: str
    requirement: str
    """The AR-* this test exists to prove."""

    breaks: str
    must_observe: str
    runnable_from: Phase
    implementation: Callable[[], DestructiveTest] | None = None

    @property
    def implemented(self) -> bool:
        return self.implementation is not None


def _impl(name: str) -> Callable[[], DestructiveTest]:
    def factory() -> DestructiveTest:
        from tests.destructive import cases

        built: DestructiveTest = getattr(cases, name)()
        return built

    return factory


REGISTRY: tuple[TestSpec, ...] = (
    TestSpec(
        id="D1",
        requirement="AR-10",
        breaks="Kill the runtime mid-schedule",
        must_observe="External monitor alerts within the window",
        runnable_from=Phase.PHASE_4,
        implementation=_impl("d1"),
    ),
    TestSpec(
        id="D2",
        requirement="AR-6",
        breaks="Alter the constitution digest",
        must_observe="VERIFY halts and does not proceed",
        runnable_from=Phase.PHASE_3,
        implementation=_impl("d2"),
    ),
    TestSpec(
        id="D3",
        requirement="AR-3",
        breaks="Attempt a capability directly from the runtime",
        must_observe="Fails: there is no sts:AssumeRole to attempt it with",
        runnable_from=Phase.PHASE_3,
        implementation=_impl("d3"),
    ),
    TestSpec(
        id="D4",
        requirement="AR-15",
        breaks="Replay an identical request",
        must_observe="Exactly one side effect; second result is DUPLICATE",
        runnable_from=Phase.PHASE_2,
        implementation=_impl("d4"),
    ),
    TestSpec(
        id="D5",
        requirement="AR-16",
        breaks="Submit an undeclared capability id",
        must_observe="Rejected at ingress, before policy evaluation runs",
        runnable_from=Phase.PHASE_2,
        implementation=_impl("d5"),
    ),
    TestSpec(
        id="D6",
        requirement="AR-7",
        breaks="Submit a well-formed request with out-of-scope parameters",
        must_observe="DENIED, and the response names the deciding rule",
        runnable_from=Phase.PHASE_2,
        implementation=_impl("d6"),
    ),
    TestSpec(
        id="D7",
        requirement="AR-4",
        breaks="Revoke the broker's audit write permission",
        must_observe="AUDIT OPEN fails; execution does not occur",
        runnable_from=Phase.PHASE_2,
        implementation=_impl("d7"),
    ),
    TestSpec(
        id="D8",
        requirement="AR-4",
        breaks="Fail AUDIT CLOSE after a successful provider call",
        must_observe=(
            "Outcome UNKNOWN, claim non-terminal, incident raised -- never FAILURE; "
            "reconciliation then resolves it"
        ),
        runnable_from=Phase.PHASE_2,
        implementation=_impl("d8"),
    ),
)

BY_ID: dict[str, TestSpec] = {spec.id: spec for spec in REGISTRY}


@contextmanager
def destructively(test: DestructiveTest) -> Iterator[None]:
    """Break, yield for assertions, always restore.

    Restore runs on the failure path too. A control left disabled by a failed run turns one
    red test into a silently unprotected system.
    """
    test.break_it()
    try:
        yield
    finally:
        test.restore()


def unimplemented() -> tuple[TestSpec, ...]:
    return tuple(spec for spec in REGISTRY if not spec.implemented)


def summary() -> str:
    lines = [f"{'ID':<4} {'AR':<6} {'FROM':<9} {'STATUS':<14} BREAKS"]
    for spec in REGISTRY:
        status = "implemented" if spec.implemented else "not implemented"
        lines.append(
            f"{spec.id:<4} {spec.requirement:<6} {spec.runnable_from:<9} {status:<14} {spec.breaks}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(summary())
