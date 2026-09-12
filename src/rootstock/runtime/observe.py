"""OBSERVE: assemble the deterministic payload. No free text, no external content."""

from __future__ import annotations

import hashlib
from typing import Any

from rootstock.runtime.reasoner import LastCycle, Observation
from rootstock.runtime.stores import DecisionRecord
from rootstock.shared.canonical import canonical_json
from rootstock.shared.vocabulary import SANDBOX_BUCKET_PREFIX


def observation_from_state(
    *,
    cycle_number: int,
    constitution_version: str,
    capabilities_granted: tuple[str, ...],
    prior: DecisionRecord | None,
    closed: list[DecisionRecord],
    memory_summary: tuple[dict[str, Any], ...],
) -> Observation:
    inventory = inventory_from_decisions(closed)
    last = last_cycle_from(prior, inventory) if prior is not None else None
    failures = 0
    for rec in reversed(closed):
        if rec.actual_outcome in {"FAILURE", "UNKNOWN"}:
            failures += 1
        else:
            break
    return Observation(
        cycle_number=cycle_number,
        constitution_version=constitution_version,
        capabilities_granted=capabilities_granted,
        last_cycle=last,
        consecutive_failures=failures,
        sandbox_inventory=inventory,
        memory_summary=memory_summary,
        cost_to_date={"today_usd": 0.0, "month_usd": 0.0, "remaining_budget": 0.0},
        pending_approvals=(),
    )


def observation_payload(observation: Observation) -> dict[str, Any]:
    """JSON-shaped observation. Model input must match this; it is what we hash."""
    return {
        "cycle_number": observation.cycle_number,
        "constitution_version": observation.constitution_version,
        "capabilities_granted": list(observation.capabilities_granted),
        "last_cycle": (
            {
                "number": observation.last_cycle.number,
                "decision": observation.last_cycle.decision,
                "outcome": observation.last_cycle.outcome,
                "timestamp": observation.last_cycle.timestamp,
                "expected_outcome_met": observation.last_cycle.expected_outcome_met,
            }
            if observation.last_cycle
            else None
        ),
        "consecutive_failures": observation.consecutive_failures,
        "sandbox_inventory": list(observation.sandbox_inventory),
        "memory_summary": list(observation.memory_summary),
        "cost_to_date": observation.cost_to_date,
        "pending_approvals": list(observation.pending_approvals),
    }


def inventory_from_decisions(closed: list[DecisionRecord]) -> tuple[dict[str, Any], ...]:
    items: list[dict[str, Any]] = []
    for rec in closed:
        result = rec.result_json or {}
        for artifact in result.get("artifacts") or ():
            name = str(artifact).removeprefix("s3://")
            if name.startswith(SANDBOX_BUCKET_PREFIX):
                items.append(
                    {
                        "name": name,
                        "cycle": rec.cycle_number,
                        "source": "decision_artifact",
                    }
                )
    return tuple(items)


def last_cycle_from(prior: DecisionRecord, inventory: tuple[dict[str, Any], ...]) -> LastCycle:
    met = expected_outcome_met(prior, inventory)
    return LastCycle(
        number=prior.cycle_number,
        decision=prior.decision,
        outcome=prior.actual_outcome or prior.state,
        timestamp=str(prior.opened_at),
        expected_outcome_met=met,
    )


def expected_outcome_met(
    prior: DecisionRecord, inventory: tuple[dict[str, Any], ...]
) -> bool | None:
    if prior.state != "closed":
        return None
    if prior.capability is None:
        return True
    result = prior.result_json or {}
    outcome = str(result.get("outcome") or prior.actual_outcome or "")
    if prior.expected_outcome and "bucket" in prior.expected_outcome:
        names = {str(item["name"]) for item in inventory}
        request = prior.request_json or {}
        suffix = str((request.get("parameters") or {}).get("suffix") or "")
        wanted = f"{SANDBOX_BUCKET_PREFIX}{suffix}" if suffix else ""
        return wanted in names and outcome == "SUCCESS"
    return outcome in {"SUCCESS", "DENIED", "REJECTED", "DUPLICATE"}


def observation_hash(observation: Observation) -> str:
    digest = hashlib.sha256(canonical_json(observation_payload(observation))).hexdigest()
    return digest
