"""Broker pipeline: schema → policy → claim → audit open → execute → audit close.

Ordering is the architecture. Do not reorder these steps to make a test pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from rootstock.broker.errors import AuditWriteError, ExecuteError, IngressError, error_body
from rootstock.broker.executor import Executor, bucket_name
from rootstock.broker.grant_store import GrantStore
from rootstock.broker.policy import PolicyEffect, evaluate_policy
from rootstock.broker.schema import validate_request
from rootstock.broker.session_policy import bind_session_policy
from rootstock.broker.stores import (
    LEASE_SECONDS,
    ApprovalRecord,
    ApprovalStore,
    ClaimRecord,
    ClaimStore,
    Clock,
    DecisionCloser,
    IncidentSink,
    SystemClock,
)
from rootstock.shared.capability import CapabilityRequest, CapabilityResult, Cost, Outcome
from rootstock.shared.claims import ApprovalState, ClaimState
from rootstock.shared.identity import canonical_request_id
from rootstock.shared.vocabulary import SANDBOX_S3_CREATE_BUCKET


class AuditLog(Protocol):
    def open_record(self, canonical_id: str, body: dict[str, Any]) -> str: ...
    def close_record(self, canonical_id: str, body: dict[str, Any]) -> None: ...


@dataclass
class Broker:
    grants: GrantStore
    claims: ClaimStore
    approvals: ApprovalStore
    audit: AuditLog
    executor: Executor
    incidents: IncidentSink
    decisions: DecisionCloser
    clock: Clock

    def process(self, request: CapabilityRequest) -> CapabilityResult:
        cid = canonical_request_id(request)
        try:
            validate_request(request, self.grants)
        except IngressError as exc:
            return CapabilityResult(
                outcome=Outcome.REJECTED,
                canonical_id=cid,
                rule=exc.rule,
                error=error_body("REJECTED", exc.message, rule=exc.rule),
            )

        existing = self.claims.get(cid)
        if existing is not None and existing.state in {ClaimState.EXECUTED, ClaimState.FAILED}:
            return _duplicate(existing)
        if (
            existing is not None
            and existing.state is ClaimState.PENDING
            and existing.lease_expires_at >= int(self.clock.now())
        ):
            return _duplicate(existing)
        if existing is not None and existing.state is ClaimState.UNKNOWN:
            return self._reconcile(request, existing)

        parked = self.approvals.get(cid)
        if parked is not None and parked.state is ApprovalState.AWAITING_APPROVAL:
            return _parked(cid, "approval.already_parked")

        decision = evaluate_policy(request, self.grants)
        if decision.effect is PolicyEffect.DENY:
            result = CapabilityResult(
                outcome=Outcome.DENIED,
                canonical_id=cid,
                rule=decision.rule,
                error=error_body("DENIED", "policy denied", rule=decision.rule),
            )
            self.decisions.close(request.decision_ref, result)
            return result
        if decision.effect is PolicyEffect.REQUIRE_APPROVAL:
            self.approvals.put(
                ApprovalRecord(
                    canonical_id=cid,
                    state=ApprovalState.AWAITING_APPROVAL,
                    request=request.as_json(),
                    expires_at=int(self.clock.now()) + 7 * 24 * 3600,
                )
            )
            return _parked(cid, decision.rule)

        attempt = self.claims.try_claim(cid, self.clock.now())
        if attempt.duplicate:
            return _duplicate(attempt.record)
        if attempt.needs_reconcile:
            return self._reconcile(request, attempt.record)

        record = attempt.record
        if record.attempt > 1:
            reconciled = self._reconcile_before_retry(request, record)
            if reconciled is not None:
                return reconciled

        return self._execute_allowed(request, record, decision.rule)

    def _execute_allowed(
        self,
        request: CapabilityRequest,
        record: ClaimRecord,
        policy_rule: str,
    ) -> CapabilityResult:
        cid = record.canonical_id
        open_body = {
            "canonical_id": cid,
            "capability": request.capability,
            "parameters": request.parameters,
            "policy_rule": policy_rule,
            "intended_action": "create_bucket",
            "attempt": record.attempt,
        }
        try:
            audit_id = self.audit.open_record(cid, open_body)
        except AuditWriteError as exc:
            record.lease_expires_at = int(self.clock.now()) - 1
            self.claims.save(record)
            return CapabilityResult(
                outcome=Outcome.FAILURE,
                canonical_id=cid,
                rule="audit.open",
                error=error_body("AUDIT_OPEN_FAILED", str(exc)),
            )

        record.audit_id = audit_id
        self.claims.save(record)

        if request.capability != SANDBOX_S3_CREATE_BUCKET:
            record.lease_expires_at = int(self.clock.now()) - 1
            self.claims.save(record)
            return CapabilityResult(
                outcome=Outcome.FAILURE,
                canonical_id=cid,
                audit_id=audit_id,
                rule="executor.unimplemented",
                error=error_body("UNIMPLEMENTED", request.capability),
            )

        suffix = str(request.parameters["suffix"])
        purpose = str(request.parameters["purpose"])
        name = bucket_name(suffix)
        template = self.grants.session_policy_template(request.capability)
        if template is None:
            record.lease_expires_at = int(self.clock.now()) - 1
            self.claims.save(record)
            return CapabilityResult(
                outcome=Outcome.FAILURE,
                canonical_id=cid,
                audit_id=audit_id,
                rule="executor.session_policy",
                error=error_body("SESSION_POLICY_MISSING", request.capability),
            )
        session_policy = bind_session_policy(template, bucket_arn=f"arn:aws:s3:::{name}")

        try:
            executed = self.executor.create_bucket(
                suffix=suffix,
                purpose=purpose,
                canonical_id=cid,
                session_policy=session_policy,
            )
        except ExecuteError as exc:
            return self._unknown(
                request,
                record,
                audit_id,
                reason="execute_unconfirmed",
                detail={"message": str(exc)},
            )

        close_body = {
            "canonical_id": cid,
            "outcome": "SUCCESS",
            "bucket": executed.bucket,
            "tags": executed.tags,
            "audit_open_id": audit_id,
        }
        try:
            self.audit.close_record(cid, close_body)
        except AuditWriteError as exc:
            return self._unknown(
                request,
                record,
                audit_id,
                reason="audit_close_failed",
                detail={"message": str(exc), "bucket": executed.bucket},
            )

        result = CapabilityResult(
            outcome=Outcome.SUCCESS,
            canonical_id=cid,
            actual_cost=Cost(usd=0.0, duration_ms=0),
            artifacts=(f"s3://{executed.bucket}",),
            audit_id=audit_id,
            rule=policy_rule,
        )
        record.state = ClaimState.EXECUTED
        record.result = result
        record.lease_expires_at = int(self.clock.now())
        self.claims.save(record)
        self.decisions.close(request.decision_ref, result)
        return result

    def _unknown(
        self,
        request: CapabilityRequest,
        record: ClaimRecord,
        audit_id: str,
        *,
        reason: str,
        detail: dict[str, Any],
    ) -> CapabilityResult:
        result = CapabilityResult(
            outcome=Outcome.UNKNOWN,
            canonical_id=record.canonical_id,
            audit_id=audit_id,
            rule=reason,
            error=error_body("UNKNOWN", reason, **detail),
        )
        record.state = ClaimState.UNKNOWN
        record.result = result
        record.incident = True
        self.claims.save(record)
        self.incidents.raise_incident(record.canonical_id, reason, detail)
        self.decisions.close(request.decision_ref, result)
        return result

    def _reconcile_before_retry(
        self, request: CapabilityRequest, record: ClaimRecord
    ) -> CapabilityResult | None:
        if request.capability != SANDBOX_S3_CREATE_BUCKET:
            return None
        name = bucket_name(str(request.parameters["suffix"]))
        if self.executor.bucket_exists(name):
            return self._close_reconciled(request, record, name, existed=True)
        return None

    def _reconcile(self, request: CapabilityRequest, record: ClaimRecord) -> CapabilityResult:
        if request.capability != SANDBOX_S3_CREATE_BUCKET:
            self.incidents.raise_incident(
                record.canonical_id, "reconcile_unimplemented", {"capability": request.capability}
            )
            return record.result or CapabilityResult(
                outcome=Outcome.UNKNOWN,
                canonical_id=record.canonical_id,
                rule="reconcile.unimplemented",
            )
        name = bucket_name(str(request.parameters["suffix"]))
        exists = self.executor.bucket_exists(name)
        return self._close_reconciled(request, record, name, existed=exists)

    def _close_reconciled(
        self,
        request: CapabilityRequest,
        record: ClaimRecord,
        bucket: str,
        *,
        existed: bool,
    ) -> CapabilityResult:
        outcome = Outcome.SUCCESS if existed else Outcome.FAILURE
        state = ClaimState.EXECUTED if existed else ClaimState.FAILED
        close_body = {
            "canonical_id": record.canonical_id,
            "outcome": str(outcome),
            "reconciled": True,
            "bucket": bucket,
            "existed": existed,
        }
        try:
            self.audit.close_record(record.canonical_id, close_body)
        except AuditWriteError as exc:
            self.incidents.raise_incident(
                record.canonical_id, "reconcile_audit_close_failed", {"message": str(exc)}
            )
            if record.result is not None:
                return record.result
            return CapabilityResult(
                outcome=Outcome.UNKNOWN,
                canonical_id=record.canonical_id,
                rule="reconcile.audit_close",
            )
        result = CapabilityResult(
            outcome=outcome,
            canonical_id=record.canonical_id,
            artifacts=(f"s3://{bucket}",) if existed else (),
            audit_id=record.audit_id,
            rule="reconcile.provider",
        )
        record.state = state
        record.result = result
        record.lease_expires_at = int(self.clock.now())
        self.claims.save(record)
        self.decisions.close(request.decision_ref, result)
        return result


def _duplicate(record: ClaimRecord) -> CapabilityResult:
    prior = record.result
    return CapabilityResult(
        outcome=Outcome.DUPLICATE,
        canonical_id=record.canonical_id,
        artifacts=prior.artifacts if prior else (),
        audit_id=record.audit_id or (prior.audit_id if prior else None),
        error=error_body(
            "DUPLICATE",
            "already claimed",
            prior_outcome=str(prior.outcome) if prior else str(record.state),
        ),
    )


def _parked(canonical_id: str, rule: str) -> CapabilityResult:
    return CapabilityResult(
        outcome=Outcome.DENIED,
        canonical_id=canonical_id,
        rule=rule,
        error=error_body("AWAITING_APPROVAL", "parked; no claim taken", rule=rule),
    )


def in_memory_broker(
    *,
    grants: GrantStore | None = None,
    executor: Executor | None = None,
    audit: AuditLog | None = None,
    clock: Clock | None = None,
) -> Broker:
    from rootstock.broker.executor import FakeExecutor
    from rootstock.broker.grant_store import default_grant_store
    from rootstock.broker.stores import (
        MemoryApprovalStore,
        MemoryAudit,
        MemoryClaimStore,
        MemoryIncidents,
        NullDecisionCloser,
    )

    return Broker(
        grants=grants or default_grant_store(),
        claims=MemoryClaimStore(),
        approvals=MemoryApprovalStore(),
        audit=audit or MemoryAudit(),
        executor=executor or FakeExecutor(),
        incidents=MemoryIncidents(),
        decisions=NullDecisionCloser(),
        clock=clock or SystemClock(),
    )


# Re-export so tests can pin the lease window to the protocol.
LEASE_SECONDS = LEASE_SECONDS
