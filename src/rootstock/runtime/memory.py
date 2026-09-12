"""Institutional memory claims. Persistence is the runtime's; this is the schema."""

from __future__ import annotations

from typing import Any

from rootstock.runtime.stores import DecisionRecord

CLAIM_FIELDS = (
    "claim",
    "evidence",
    "derived_from",
    "timestamp",
    "confidence",
    "applicability",
    "last_validated",
    "expires",
    "status",
)

SIX_MONTHS = 180 * 24 * 60 * 60
NOOP_EXPECTED = "No Sandbox mutation occurs this cycle."


def claim_from_prior(prior: DecisionRecord, *, met: bool | None, now: int) -> dict[str, Any]:
    """One self-observation about a closed or halted prior cycle."""
    outcome = str(prior.actual_outcome or prior.reason or "unknown")
    if met is True:
        expectation = "met"
    elif met is False:
        expectation = "not met"
    else:
        expectation = "not applicable"
    return {
        "claim": (
            f"Cycle {prior.cycle_number} outcome was {outcome}; expected_outcome {expectation}."
        ),
        "evidence": {
            "cycle_number": prior.cycle_number,
            "canonical_id": prior.canonical_id,
            "actual_outcome": prior.actual_outcome,
            "expected_outcome": prior.expected_outcome,
            "expected_outcome_met": met,
            "capability": prior.capability,
        },
        "derived_from": ["decision", f"cycle:{prior.cycle_number}"],
        "timestamp": now,
        "confidence": "low",
        "applicability": "sandbox; us-east-1; v0-loop",
        "last_validated": now,
        "expires": now + SIX_MONTHS,
        "status": "active",
    }
