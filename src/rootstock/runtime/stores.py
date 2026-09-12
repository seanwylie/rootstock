"""Runtime stores: cursor, decisions, memory, grant reads. No side-effect authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from rootstock.shared.claims import ApprovalState, ClaimState


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    cycle_number: int
    state: str
    opened_by: str
    opened_at: int
    closed_by: str | None = None
    observed_hash: str | None = None
    expected_outcome: str | None = None
    capability: str | None = None
    canonical_id: str | None = None
    request_json: dict[str, Any] | None = None
    result_json: dict[str, Any] | None = None
    actual_outcome: str | None = None
    reason: str | None = None
    alternatives: tuple[str, ...] = ()
    rationale: str = ""
    decision: str = ""


@dataclass(frozen=True, slots=True)
class Cursor:
    next_cycle: int


class DecisionStore(Protocol):
    def get(self, cycle_number: int) -> DecisionRecord | None: ...
    def open(self, record: DecisionRecord) -> None: ...
    def list_closed(self, through_cycle: int) -> list[DecisionRecord]: ...


class CursorStore(Protocol):
    def get(self) -> Cursor: ...
    def save(self, cursor: Cursor) -> None: ...


class MemoryLog(Protocol):
    def append(self, cycle_number: int, body: dict[str, Any]) -> None: ...
    def recent(self, limit: int = 8) -> list[dict[str, Any]]: ...
    def record_wake(
        self, *, at: int, outcome: str, reason: str, cycle_number: int | None = None
    ) -> None: ...


class ClaimReader(Protocol):
    def get_state(self, canonical_id: str) -> tuple[ClaimState | None, int | None]: ...


class ApprovalReader(Protocol):
    def get_state(self, canonical_id: str) -> ApprovalState | None: ...


class Constitution(Protocol):
    def digest(self) -> str: ...
    def granted_ids(self, actor: str) -> tuple[str, ...]: ...


class Enqueue(Protocol):
    def send(self, body: dict[str, Any]) -> None: ...


@dataclass
class MemoryDecisionStore:
    rows: dict[int, DecisionRecord] = field(default_factory=dict)

    def get(self, cycle_number: int) -> DecisionRecord | None:
        return self.rows.get(cycle_number)

    def open(self, record: DecisionRecord) -> None:
        if record.cycle_number in self.rows:
            raise RuntimeError(f"decision {record.cycle_number} already exists")
        self.rows[record.cycle_number] = record

    def replace(self, record: DecisionRecord) -> None:
        self.rows[record.cycle_number] = record

    def list_closed(self, through_cycle: int) -> list[DecisionRecord]:
        out: list[DecisionRecord] = []
        for n in range(1, through_cycle + 1):
            rec = self.rows.get(n)
            if rec is not None and rec.state == "closed":
                out.append(rec)
        return out


@dataclass
class MemoryCursorStore:
    next_cycle: int = 1

    def get(self) -> Cursor:
        return Cursor(next_cycle=self.next_cycle)

    def save(self, cursor: Cursor) -> None:
        self.next_cycle = cursor.next_cycle


@dataclass
class MemoryLogStore:
    items: list[dict[str, Any]] = field(default_factory=list)
    wakes: list[dict[str, Any]] = field(default_factory=list)

    def append(self, cycle_number: int, body: dict[str, Any]) -> None:
        self.items.append({"cycle_number": cycle_number, **body})

    def recent(self, limit: int = 8) -> list[dict[str, Any]]:
        return list(self.items[-limit:])

    def record_wake(
        self, *, at: int, outcome: str, reason: str, cycle_number: int | None = None
    ) -> None:
        self.wakes.append(
            {"at": at, "outcome": outcome, "reason": reason, "cycle_number": cycle_number}
        )


@dataclass
class MemoryQueue:
    messages: list[dict[str, Any]] = field(default_factory=list)

    def send(self, body: dict[str, Any]) -> None:
        self.messages.append(body)

    def drain(self) -> list[dict[str, Any]]:
        out = list(self.messages)
        self.messages.clear()
        return out
