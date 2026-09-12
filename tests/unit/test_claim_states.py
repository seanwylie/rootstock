"""F-1: waiting for approval must not look like a dead broker."""

from __future__ import annotations

from rootstock.shared.claims import (
    IN_FLIGHT_CLAIM_STATES,
    PARKED_APPROVAL_STATES,
    TERMINAL_CLAIM_STATES,
    ApprovalState,
    ClaimState,
    verify_prior_cycle,
)


def test_unknown_is_in_flight_not_terminal() -> None:
    assert ClaimState.UNKNOWN in IN_FLIGHT_CLAIM_STATES
    assert ClaimState.UNKNOWN not in TERMINAL_CLAIM_STATES


def test_awaiting_approval_is_not_a_claim_state() -> None:
    assert "AWAITING_APPROVAL" not in {s.value for s in ClaimState}
    assert ApprovalState.AWAITING_APPROVAL in PARKED_APPROVAL_STATES


def test_parked_approval_is_proceed_not_halt() -> None:
    # This is the F-1 bug: PENDING + expired lease would halt. Parked must not.
    assert (
        verify_prior_cycle(
            decision_closed=False,
            approval_state=ApprovalState.AWAITING_APPROVAL,
            claim_state=None,
            lease_valid=False,
        )
        == "proceed_parked"
    )


def test_expired_pending_claim_halts() -> None:
    assert (
        verify_prior_cycle(
            decision_closed=False,
            approval_state=None,
            claim_state=ClaimState.PENDING,
            lease_valid=False,
        )
        == "halt"
    )


def test_valid_lease_skips() -> None:
    assert (
        verify_prior_cycle(
            decision_closed=False,
            approval_state=None,
            claim_state=ClaimState.PENDING,
            lease_valid=True,
        )
        == "skip"
    )


def test_closed_decision_proceeds() -> None:
    assert (
        verify_prior_cycle(
            decision_closed=True,
            approval_state=None,
            claim_state=ClaimState.EXECUTED,
            lease_valid=False,
        )
        == "proceed"
    )


def test_enqueue_window_without_claim_is_skip() -> None:
    assert (
        verify_prior_cycle(
            decision_closed=False,
            approval_state=None,
            claim_state=None,
            lease_valid=False,
            enqueue_window_valid=True,
        )
        == "skip"
    )


def test_unknown_claim_halts_for_reconciliation() -> None:
    assert (
        verify_prior_cycle(
            decision_closed=False,
            approval_state=None,
            claim_state=ClaimState.UNKNOWN,
            lease_valid=False,
        )
        == "halt"
    )
