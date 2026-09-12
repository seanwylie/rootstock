"""Builders for CapabilityRequest.

Lets a test drive the broker without a runtime, which is what makes Phase 2 provable before
Phase 3 exists.
"""

from __future__ import annotations

from typing import Any

from rootstock.shared import vocabulary
from rootstock.shared.capability import CapabilityRequest, Cost, Provenance

DEFAULT_ACTOR = "rootstock-runtime"


def create_bucket_request(
    *,
    idempotency_key: str = "1",
    suffix: str = "fixture",
    purpose: str = "fixture",
    actor: str = DEFAULT_ACTOR,
    provenance: Provenance = Provenance.TRUSTED,
    decision_ref: str | None = "dec_fixture",
) -> CapabilityRequest:
    """A well-formed, in-scope request. The baseline everything else deviates from."""
    return CapabilityRequest(
        idempotency_key=idempotency_key,
        actor=actor,
        capability=vocabulary.SANDBOX_S3_CREATE_BUCKET,
        target=f"{vocabulary.SANDBOX_BUCKET_PREFIX}{suffix}",
        parameters={"suffix": suffix, "purpose": purpose},
        estimated_cost=Cost(usd=0.0),
        justification="Fixture-driven request.",
        decision_ref=decision_ref,
        provenance=provenance,
    )


def undeclared_capability_request(*, idempotency_key: str = "1") -> CapabilityRequest:
    """Drives D5. The generic-proxy shape AR-16 exists to make unroutable."""
    return CapabilityRequest(
        idempotency_key=idempotency_key,
        actor=DEFAULT_ACTOR,
        capability="aws.call",
        target="s3",
        parameters={"operation": "CreateBucket", "params": {"Bucket": "anything"}},
        justification="Should be unroutable, not merely denied.",
    )


def malformed_request(*, idempotency_key: str = "1") -> CapabilityRequest:
    """Declared capability, parameters violating its schema. Expect REJECTED."""
    return CapabilityRequest(
        idempotency_key=idempotency_key,
        actor=DEFAULT_ACTOR,
        capability=vocabulary.SANDBOX_S3_CREATE_BUCKET,
        target=f"{vocabulary.SANDBOX_BUCKET_PREFIX}invalid",
        parameters={"suffix": "INVALID_Suffix!!"},
        justification="Should fail schema validation before policy runs.",
    )


def out_of_scope_request(*, idempotency_key: str = "1") -> CapabilityRequest:
    """Drives D6. Schema-valid, but the target is outside the granted prefix."""
    return CapabilityRequest(
        idempotency_key=idempotency_key,
        actor=DEFAULT_ACTOR,
        capability=vocabulary.SANDBOX_S3_PUT_OBJECT,
        target="someone-elses-bucket",
        parameters={"suffix": "fixture", "key": "x"},
        justification="Should be denied by a named scope rule.",
    )


def with_parameters(request: CapabilityRequest, **overrides: Any) -> CapabilityRequest:
    """Vary parameters while holding the idempotency key fixed.

    Used to show that the canonical id tracks content: same key plus different parameters is
    a different request, and must not be swallowed as a duplicate.
    """
    params = dict(request.parameters)
    params.update(overrides)
    return CapabilityRequest(
        idempotency_key=request.idempotency_key,
        actor=request.actor,
        capability=request.capability,
        target=request.target,
        parameters=params,
        estimated_cost=request.estimated_cost,
        justification=request.justification,
        decision_ref=request.decision_ref,
        provenance=request.provenance,
    )
