"""Claim and approval states.

F-1: the claim table is for execution. The approval store is for parking.
A lease means a process is working. Nothing is working on a request waiting for the operator.
"""

from __future__ import annotations

from enum import StrEnum


class ClaimState(StrEnum):
    PENDING = "PENDING"
    """Broker holds a lease and is executing, or crashed while doing so."""

    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    """Side effect may have occurred; not terminal until reconciled (AR-4)."""


class ApprovalState(StrEnum):
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    """Silence past the window. Equivalent to DENY, never to an expired-lease halt."""


IN_FLIGHT_CLAIM_STATES = frozenset({ClaimState.PENDING, ClaimState.UNKNOWN})
TERMINAL_CLAIM_STATES = frozenset({ClaimState.EXECUTED, ClaimState.FAILED})
PARKED_APPROVAL_STATES = frozenset({ApprovalState.AWAITING_APPROVAL})


def verify_prior_cycle(
    *,
    decision_closed: bool,
    approval_state: ApprovalState | None,
    claim_state: ClaimState | None,
    lease_valid: bool,
    enqueue_window_valid: bool = False,
) -> str:
    """Return the VERIFY action for a prior cycle.

    Values: proceed | proceed_parked | skip | halt

    ``enqueue_window_valid`` covers the gap after DECIDE and before the broker
    claims: the request is in SQS, there is no lease yet, and skipping is
    impatience rather than a dead broker.
    """
    if decision_closed:
        return "proceed"
    if approval_state in PARKED_APPROVAL_STATES:
        return "proceed_parked"
    if claim_state is ClaimState.PENDING and lease_valid:
        return "skip"
    if claim_state is ClaimState.PENDING and not lease_valid:
        return "halt"
    if claim_state is ClaimState.UNKNOWN:
        return "halt"
    if claim_state is None and enqueue_window_valid:
        return "skip"
    if approval_state is ApprovalState.EXPIRED:
        return "proceed"
    return "halt"
