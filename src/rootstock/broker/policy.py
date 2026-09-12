"""Deterministic policy. First DENY wins (AR-3). Runs before any claim (F-1)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from rootstock.broker.grant_store import GrantStore, matches_never_granted
from rootstock.shared.capability import CapabilityRequest, Provenance
from rootstock.shared.vocabulary import SANDBOX_BUCKET_PREFIX


class PolicyEffect(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    effect: PolicyEffect
    rule: str
    cost_ceiling_usd: float = 0.01


def evaluate_policy(request: CapabilityRequest, store: GrantStore) -> PolicyDecision:
    policy = store.policy()
    decl = store.capability(request.capability)
    assert decl is not None  # schema validation already required this

    granted_anywhere = any(request.capability in caps for caps in policy.grants.values())
    if not granted_anywhere:
        return PolicyDecision(PolicyEffect.DENY, "grant.capability")

    actor_grants = policy.grants.get(request.actor, frozenset())
    if request.capability not in actor_grants:
        return PolicyDecision(PolicyEffect.DENY, "grant.actor")

    if request.capability.startswith("sandbox.") and not request.target.startswith(
        SANDBOX_BUCKET_PREFIX
    ):
        return PolicyDecision(PolicyEffect.DENY, "scope.target")

    if request.capability.startswith("sandbox.s3.") and "suffix" in request.parameters:
        expected = f"{SANDBOX_BUCKET_PREFIX}{request.parameters['suffix']}"
        if request.target != expected:
            return PolicyDecision(PolicyEffect.DENY, "scope.target")

    if matches_never_granted(request.capability, policy.never_granted):
        return PolicyDecision(PolicyEffect.DENY, "constitution.never_granted")

    if request.provenance is Provenance.DERIVED_FROM_UNTRUSTED:
        return PolicyDecision(PolicyEffect.DENY, "provenance.untrusted")

    if request.estimated_cost.usd > 1.0:
        return PolicyDecision(PolicyEffect.DENY, "budget.estimated")

    level = decl.autonomy_level.upper()
    if decl.requires_approval or level in {"L0"}:
        return PolicyDecision(PolicyEffect.REQUIRE_APPROVAL, "autonomy.require_approval")
    if level == "L1":
        return PolicyDecision(PolicyEffect.REQUIRE_APPROVAL, "autonomy.l1")

    if not decl.reversible and decl.requires_approval:
        return PolicyDecision(PolicyEffect.REQUIRE_APPROVAL, "irreversibility.require_approval")

    return PolicyDecision(PolicyEffect.ALLOW, "policy.allow")
