"""Ingress validation (AR-16). Malformed input never reaches policy."""

from __future__ import annotations

from typing import Any

from rootstock.broker.errors import IngressError
from rootstock.broker.grant_store import GrantStore, compile_pattern
from rootstock.shared.capability import SCHEMA_VERSION, CapabilityRequest, Cost, Provenance
from rootstock.shared.vocabulary import SANDBOX_BUCKET_PREFIX, SANDBOX_S3_CREATE_BUCKET

_SUFFIX_CAPABILITIES = {
    SANDBOX_S3_CREATE_BUCKET,
    "sandbox.s3.put_object",
    "sandbox.s3.list",
}


def validate_request(request: CapabilityRequest, store: GrantStore) -> None:
    if request.schema_version != SCHEMA_VERSION:
        raise IngressError(
            "schema.version",
            f"unknown schema_version {request.schema_version}",
        )
    if not request.idempotency_key:
        raise IngressError("schema.idempotency_key", "idempotency_key is required")
    if not request.actor:
        raise IngressError("schema.actor", "actor is required")
    if not request.capability:
        raise IngressError("schema.capability", "capability is required")

    declared = store.declared_ids()
    if request.capability not in declared:
        raise IngressError(
            "schema.undeclared_capability",
            f"{request.capability} is not a declared capability id",
        )

    decl = store.capability(request.capability)
    if decl is None:
        raise IngressError(
            "schema.undeclared_capability",
            f"{request.capability} has no grant-store declaration",
        )

    params = request.parameters
    if not isinstance(params, dict):
        raise IngressError("schema.parameters", "parameters must be an object")

    allowed = set(decl.parameter_schema)
    extra = set(params) - allowed
    if extra:
        raise IngressError(
            "schema.parameters",
            f"undeclared parameters: {sorted(extra)}",
        )

    for name, field in decl.parameter_schema.items():
        if field.required and name not in params:
            raise IngressError("schema.parameters", f"missing required parameter {name}")
        if name not in params:
            continue
        value = params[name]
        if field.type == "string" and not isinstance(value, str):
            raise IngressError("schema.parameters", f"{name} must be a string")
        if (
            field.pattern
            and isinstance(value, str)
            and not compile_pattern(field.pattern).match(value)
        ):
            raise IngressError(
                "schema.parameters",
                f"{name} does not match {field.pattern}",
            )

    if request.capability in _SUFFIX_CAPABILITIES and "suffix" in params:
        expected = f"{SANDBOX_BUCKET_PREFIX}{params['suffix']}"
        if request.capability == SANDBOX_S3_CREATE_BUCKET and request.target != expected:
            # Target is not caller-chosen: mismatch is malformed, not a scope debate.
            raise IngressError(
                "schema.target",
                "target must equal rootstock-sbx-<suffix>; the executor applies the prefix",
            )


def request_from_mapping(data: dict[str, Any]) -> CapabilityRequest:
    if not isinstance(data, dict):
        raise IngressError("schema.type", "request must be an object")
    try:
        version = int(data.get("schema_version", SCHEMA_VERSION))
    except (TypeError, ValueError) as exc:
        raise IngressError("schema.version", "schema_version must be an integer") from exc
    provenance_raw = data.get("provenance", Provenance.TRUSTED.value)
    try:
        provenance = Provenance(str(provenance_raw))
    except ValueError as exc:
        raise IngressError("schema.provenance", f"unknown provenance {provenance_raw}") from exc
    cost_raw = data.get("estimated_cost", {})
    if cost_raw is None:
        cost_raw = {}
    if not isinstance(cost_raw, dict):
        raise IngressError("schema.estimated_cost", "estimated_cost must be an object")
    parameters = data.get("parameters", {})
    if parameters is None:
        parameters = {}
    if not isinstance(parameters, dict):
        raise IngressError("schema.parameters", "parameters must be an object")
    return CapabilityRequest(
        idempotency_key=str(data.get("idempotency_key", "")),
        actor=str(data.get("actor", "")),
        capability=str(data.get("capability", "")),
        target=str(data.get("target", "")),
        parameters=dict(parameters),
        estimated_cost=Cost(
            usd=float(cost_raw.get("usd", 0) or 0),
            tokens=int(cost_raw.get("tokens", 0) or 0),
            duration_ms=int(cost_raw.get("duration_ms", 0) or 0),
        ),
        justification=str(data.get("justification", "")),
        decision_ref=str(data["decision_ref"]) if data.get("decision_ref") is not None else None,
        provenance=provenance,
        schema_version=version,
    )
