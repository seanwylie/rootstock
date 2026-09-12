"""In-memory stores for the broker protocol. No AWS."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from rootstock.shared.capability import CapabilityResult
from rootstock.shared.claims import ApprovalState, ClaimState

LEASE_SECONDS = 180


@dataclass
class ClaimRecord:
    canonical_id: str
    state: ClaimState
    lease_expires_at: int
    attempt: int
    result: CapabilityResult | None = None
    incident: bool = False
    audit_id: str | None = None


@dataclass
class ApprovalRecord:
    canonical_id: str
    state: ApprovalState
    request: dict[str, Any]
    expires_at: int


class Clock(Protocol):
    def now(self) -> float: ...


class SystemClock:
    def now(self) -> float:
        import time

        return time.time()


class FrozenClock:
    def __init__(self, t: float) -> None:
        self.t = t

    def now(self) -> float:
        return self.t


@dataclass
class ClaimAttempt:
    record: ClaimRecord
    duplicate: bool = False
    needs_reconcile: bool = False


class ClaimStore(Protocol):
    def get(self, canonical_id: str) -> ClaimRecord | None: ...
    def try_claim(self, canonical_id: str, now: float) -> ClaimAttempt: ...
    def save(self, record: ClaimRecord) -> None: ...
    def delete(self, canonical_id: str) -> None: ...


class ApprovalStore(Protocol):
    def get(self, canonical_id: str) -> ApprovalRecord | None: ...
    def put(self, record: ApprovalRecord) -> None: ...


class DecisionCloser(Protocol):
    def close(self, decision_ref: str | None, result: CapabilityResult) -> None: ...


class IncidentSink(Protocol):
    def raise_incident(self, canonical_id: str, reason: str, detail: dict[str, Any]) -> None: ...


class MemoryClaimStore:
    def __init__(self) -> None:
        self.rows: dict[str, ClaimRecord] = {}

    def get(self, canonical_id: str) -> ClaimRecord | None:
        return self.rows.get(canonical_id)

    def try_claim(self, canonical_id: str, now: float) -> ClaimAttempt:
        existing = self.rows.get(canonical_id)
        if existing is None:
            record = ClaimRecord(
                canonical_id=canonical_id,
                state=ClaimState.PENDING,
                lease_expires_at=int(now) + LEASE_SECONDS,
                attempt=1,
            )
            self.rows[canonical_id] = record
            return ClaimAttempt(record=record)
        if existing.state in {ClaimState.EXECUTED, ClaimState.FAILED}:
            return ClaimAttempt(record=existing, duplicate=True)
        if existing.state is ClaimState.UNKNOWN:
            return ClaimAttempt(record=existing, needs_reconcile=True)
        if existing.state is ClaimState.PENDING and existing.lease_expires_at >= int(now):
            return ClaimAttempt(record=existing, duplicate=True)
        existing.attempt += 1
        existing.state = ClaimState.PENDING
        existing.lease_expires_at = int(now) + LEASE_SECONDS
        return ClaimAttempt(record=existing)

    def save(self, record: ClaimRecord) -> None:
        self.rows[record.canonical_id] = record

    def delete(self, canonical_id: str) -> None:
        self.rows.pop(canonical_id, None)


class MemoryApprovalStore:
    def __init__(self) -> None:
        self.rows: dict[str, ApprovalRecord] = {}

    def get(self, canonical_id: str) -> ApprovalRecord | None:
        return self.rows.get(canonical_id)

    def put(self, record: ApprovalRecord) -> None:
        self.rows[record.canonical_id] = record


class MemoryIncidents:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, Any]]] = []

    def raise_incident(self, canonical_id: str, reason: str, detail: dict[str, Any]) -> None:
        self.events.append((canonical_id, reason, detail))


class NullDecisionCloser:
    def close(self, decision_ref: str | None, result: CapabilityResult) -> None:
        return None


@dataclass
class MemoryAudit:
    fail_open: bool = False
    fail_close: bool = False
    opens: dict[str, dict[str, Any]] = field(default_factory=dict)
    closes: dict[str, dict[str, Any]] = field(default_factory=dict)

    def open_record(self, canonical_id: str, body: dict[str, Any]) -> str:
        from rootstock.broker.errors import AuditWriteError

        if self.fail_open:
            raise AuditWriteError("audit open failed")
        self.opens[canonical_id] = body
        return f"aud_{canonical_id[:16]}"

    def close_record(self, canonical_id: str, body: dict[str, Any]) -> None:
        from rootstock.broker.errors import AuditWriteError

        if self.fail_close:
            raise AuditWriteError("audit close failed")
        self.closes[canonical_id] = body
