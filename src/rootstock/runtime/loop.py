"""WAKE → VERIFY → OBSERVE → LEARN → REASON → DECIDE → DORMANT.

The runtime predicts and sleeps. It never waits for the broker, never assumes a role,
and never holds process state across invocations.
"""

from __future__ import annotations

import hashlib
import logging
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any

from rootstock.broker.grant_store import GrantStore
from rootstock.broker.stores import LEASE_SECONDS, Clock, SystemClock
from rootstock.runtime.heartbeat import Heartbeat, NoopHeartbeat
from rootstock.runtime.liveness import LivenessSink, NoopLiveness
from rootstock.runtime.memory import NOOP_EXPECTED, claim_from_prior
from rootstock.runtime.observe import expected_outcome_met, observation_from_state, observation_hash
from rootstock.runtime.reasoner import Observation, Proposal, Reasoner, StubMode, StubReasoner
from rootstock.runtime.stores import (
    ApprovalReader,
    ClaimReader,
    Cursor,
    CursorStore,
    DecisionRecord,
    DecisionStore,
    Enqueue,
    MemoryLog,
)
from rootstock.shared.claims import ClaimState, verify_prior_cycle
from rootstock.shared.identity import canonical_request_id
from rootstock.shared.vocabulary import DECLARED_AT_V0

logger = logging.getLogger("rootstock.runtime")

ACTOR = "rootstock-runtime"


class VerifyHaltError(Exception):
    """VERIFY failed closed. Do not OBSERVE, do not enqueue."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class CycleResult:
    cycle_number: int
    action: str
    reason: str
    expected_outcome_met: bool | None = None
    observed_hash: str | None = None
    canonical_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None

    def as_json(self) -> dict[str, Any]:
        return {
            "cycle_number": self.cycle_number,
            "action": self.action,
            "reason": self.reason,
            "expected_outcome_met": self.expected_outcome_met,
            "observed_hash": self.observed_hash,
            "canonical_id": self.canonical_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


class DigestConstitution:
    """Grant-store backed constitution check. Expected digest is deploy-time, not S3."""

    def __init__(self, grants: GrantStore, *, expected_digest: str, body: bytes) -> None:
        self._grants = grants
        self.expected_digest = expected_digest
        self._body = body

    def digest(self) -> str:
        return hashlib.sha256(self._body).hexdigest()

    def granted_ids(self, actor: str) -> tuple[str, ...]:
        granted = self._grants.policy().grants.get(actor, frozenset())
        return tuple(sorted(granted or DECLARED_AT_V0))


@dataclass
class CycleRunner:
    constitution: DigestConstitution
    grants: GrantStore
    decisions: DecisionStore
    cursor: CursorStore
    memory: MemoryLog
    claims: ClaimReader
    approvals: ApprovalReader
    enqueue: Enqueue
    reasoner: Reasoner
    clock: Clock
    heartbeat: Heartbeat = field(default_factory=NoopHeartbeat)
    liveness: LivenessSink = field(default_factory=NoopLiveness)

    def run(self) -> CycleResult:
        try:
            return self._cycle()
        finally:
            try:
                self.heartbeat.ping()
            except Exception:
                logger.exception("heartbeat.ping failed")

    def _cycle(self) -> CycleResult:
        now = int(self.clock.now())
        result = self._cycle_body(now)
        self._record_wake(now, result)
        return result

    def _record_wake(self, now: int, result: CycleResult) -> None:
        if result.action == "skipped":
            outcome = "skip"
            cycle_number = None
        elif result.action == "halted":
            outcome = "halt"
            cycle_number = result.cycle_number if result.cycle_number > 0 else None
        else:
            outcome = "cycle"
            cycle_number = result.cycle_number
        self.memory.record_wake(
            at=now,
            outcome=outcome,
            reason=result.reason,
            cycle_number=cycle_number,
        )

    def _cycle_body(self, now: int) -> CycleResult:
        try:
            self._verify_constitution()
        except VerifyHaltError as exc:
            logger.critical("VERIFY halt: %s", exc.reason)
            return CycleResult(cycle_number=0, action="halted", reason=exc.reason)

        cursor = self.cursor.get()
        cycle = cursor.next_cycle
        prior = self.decisions.get(cycle - 1) if cycle > 1 else None

        if prior is not None:
            action = self._prior_action(prior, now)
            if action == "skip":
                logger.info("skip cycle=%s prior still in flight", cycle)
                return CycleResult(
                    cycle_number=cycle,
                    action="skipped",
                    reason="prior_lease_valid",
                )
            if action == "halt":
                logger.critical("VERIFY halt: prior lease expired cycle=%s", cycle)
                self.liveness.expired_lease(cycle)
                halted = DecisionRecord(
                    cycle_number=cycle,
                    state="halted",
                    opened_by="runtime",
                    opened_at=now,
                    closed_by="runtime",
                    reason="prior_lease_expired",
                    decision="halt",
                )
                with suppress(RuntimeError):
                    self.decisions.open(halted)
                return CycleResult(
                    cycle_number=cycle,
                    action="halted",
                    reason="prior_lease_expired",
                )

        closed = self.decisions.list_closed(max(cycle - 1, 0))
        met = (
            expected_outcome_met(
                prior,
                observation_from_state(
                    cycle_number=cycle,
                    constitution_version=self.constitution.expected_digest,
                    capabilities_granted=self.constitution.granted_ids(ACTOR),
                    prior=prior,
                    closed=closed,
                    memory_summary=(),
                ).sandbox_inventory,
            )
            if prior is not None
            else None
        )

        if prior is not None:
            self.memory.append(
                prior.cycle_number,
                claim_from_prior(prior, met=met, now=now),
            )

        observation = observation_from_state(
            cycle_number=cycle,
            constitution_version=self.constitution.expected_digest,
            capabilities_granted=self.constitution.granted_ids(ACTOR),
            prior=prior,
            closed=closed,
            memory_summary=tuple(self.memory.recent()),
        )
        digest = observation_hash(observation)
        proposal = self.reasoner.propose(observation)
        return self._decide(cycle, now, observation, digest, proposal, met)

    def _tokens(self) -> tuple[int | None, int | None]:
        raw = getattr(self.reasoner, "last_usage", None)
        if not isinstance(raw, dict):
            return None, None
        inp = raw.get("input_tokens")
        out = raw.get("output_tokens")
        return (
            int(inp) if inp is not None else None,
            int(out) if out is not None else None,
        )

    def _verify_constitution(self) -> None:
        try:
            actual = self.constitution.digest()
            self.grants.policy()
        except Exception as exc:
            raise VerifyHaltError(f"grant_store_unreadable:{exc}") from exc
        if actual != self.constitution.expected_digest:
            raise VerifyHaltError("constitution_digest_mismatch")

    def _prior_action(self, prior: DecisionRecord, now: int) -> str:
        if prior.state in {"closed", "halted", "skipped"}:
            return "proceed"
        canonical_id = prior.canonical_id
        claim_state: ClaimState | None = None
        lease_expires: int | None = None
        approval_state = None
        if canonical_id:
            claim_state, lease_expires = self.claims.get_state(canonical_id)
            approval_state = self.approvals.get_state(canonical_id)
        lease_valid = bool(lease_expires is not None and lease_expires >= now)
        enqueue_window = prior.opened_at + LEASE_SECONDS >= now
        return verify_prior_cycle(
            decision_closed=False,
            approval_state=approval_state,
            claim_state=claim_state,
            lease_valid=lease_valid,
            enqueue_window_valid=enqueue_window and claim_state is None,
        )

    def _decide(
        self,
        cycle: int,
        now: int,
        observation: Observation,
        digest: str,
        proposal: Proposal | None,
        met: bool | None,
    ) -> CycleResult:
        del observation
        if proposal is None or not str(proposal.capability).strip():
            reason = "noop"
            expected = NOOP_EXPECTED
            if proposal is not None:
                reason = str(proposal.justification or "noop")
                expected = str(proposal.expected_outcome or NOOP_EXPECTED)
            record = DecisionRecord(
                cycle_number=cycle,
                state="closed",
                opened_by="runtime",
                closed_by="runtime",
                opened_at=now,
                observed_hash=digest,
                expected_outcome=expected,
                actual_outcome="no_action",
                reason=reason,
                rationale=proposal.rationale if proposal is not None else "",
                decision="do nothing",
            )
            self.decisions.open(record)
            self.cursor.save(Cursor(next_cycle=cycle + 1))
            inp, out = self._tokens()
            return CycleResult(
                cycle_number=cycle,
                action="noop",
                reason=reason,
                expected_outcome_met=met,
                observed_hash=digest,
                input_tokens=inp,
                output_tokens=out,
            )

        request = proposal.to_request(
            actor=ACTOR,
            idempotency_key=str(cycle),
            decision_ref=str(cycle),
        )
        cid = canonical_request_id(request)
        record = DecisionRecord(
            cycle_number=cycle,
            state="open",
            opened_by="runtime",
            opened_at=now,
            observed_hash=digest,
            expected_outcome=proposal.expected_outcome,
            capability=proposal.capability,
            canonical_id=cid,
            request_json=request.as_json(),
            alternatives=proposal.alternatives,
            rationale=proposal.rationale,
            decision=proposal.justification,
        )
        self.decisions.open(record)
        self.enqueue.send(request.as_json())
        self.cursor.save(Cursor(next_cycle=cycle + 1))
        inp, out = self._tokens()
        return CycleResult(
            cycle_number=cycle,
            action="enqueued",
            reason="enqueued",
            expected_outcome_met=met,
            observed_hash=digest,
            canonical_id=cid,
            input_tokens=inp,
            output_tokens=out,
        )


def stub_from_mode(mode: str) -> StubReasoner:
    try:
        parsed = StubMode(mode)
    except ValueError:
        parsed = StubMode.NORMAL
    return StubReasoner(parsed)


def filesystem_constitution(grants: GrantStore | None = None) -> DigestConstitution:
    from pathlib import Path

    from rootstock.broker.grant_store import default_grant_store

    store = grants or default_grant_store()
    root = Path(__file__).resolve().parents[3] / "infra" / "v0" / "grant-store"
    body = (root / "constitution.json").read_bytes()
    digest = hashlib.sha256(body).hexdigest()
    return DigestConstitution(store, expected_digest=digest, body=body)


def in_memory_runtime(
    *,
    reasoner: Reasoner | None = None,
    clock: Clock | None = None,
    constitution: DigestConstitution | None = None,
) -> tuple[CycleRunner, Any]:
    """Runtime + broker sharing in-process stores. Drain the queue to simulate SQS."""
    from rootstock.broker.executor import FakeExecutor
    from rootstock.broker.grant_store import default_grant_store
    from rootstock.broker.pipeline import Broker
    from rootstock.broker.schema import request_from_mapping
    from rootstock.broker.stores import (
        MemoryApprovalStore,
        MemoryAudit,
        MemoryClaimStore,
        MemoryIncidents,
    )
    from rootstock.runtime.heartbeat import RecordingHeartbeat
    from rootstock.runtime.liveness import RecordingLiveness
    from rootstock.runtime.stores import (
        MemoryCursorStore,
        MemoryDecisionStore,
        MemoryLogStore,
        MemoryQueue,
    )

    grants = default_grant_store()
    claims = MemoryClaimStore()
    approvals = MemoryApprovalStore()
    decisions = MemoryDecisionStore()
    queue = MemoryQueue()
    executor = FakeExecutor()
    closer = _MemoryDecisionCloser(decisions)
    recorder = RecordingHeartbeat()
    live = RecordingLiveness()
    broker = Broker(
        grants=grants,
        claims=claims,
        approvals=approvals,
        audit=MemoryAudit(),
        executor=executor,
        incidents=MemoryIncidents(),
        decisions=closer,
        clock=clock or SystemClock(),
    )
    memory_log = MemoryLogStore()
    runtime = CycleRunner(
        constitution=constitution or filesystem_constitution(grants),
        grants=grants,
        decisions=decisions,
        cursor=MemoryCursorStore(),
        memory=memory_log,
        claims=_ClaimStoreReader(claims),
        approvals=_ApprovalStoreReader(approvals),
        enqueue=queue,
        reasoner=reasoner or StubReasoner(),
        clock=clock or SystemClock(),
        heartbeat=recorder,
        liveness=live,
    )

    class Harness:
        def __init__(self) -> None:
            self.runtime = runtime
            self.broker = broker
            self.queue = queue
            self.executor = executor
            self.decisions = decisions
            self.claims = claims
            self.cursor = runtime.cursor
            self.heartbeat = recorder
            self.liveness = live
            self.memory = memory_log

        def wake(self) -> CycleResult:
            return self.runtime.run()

        def drain(self) -> None:
            for body in self.queue.drain():
                self.broker.process(request_from_mapping(body))

        def wake_and_drain(self) -> CycleResult:
            result = self.wake()
            self.drain()
            return result

    return runtime, Harness()


class _ClaimStoreReader:
    def __init__(self, store: Any) -> None:
        self._store = store

    def get_state(self, canonical_id: str) -> tuple[ClaimState | None, int | None]:
        record = self._store.get(canonical_id)
        if record is None:
            return None, None
        return record.state, record.lease_expires_at


class _ApprovalStoreReader:
    def __init__(self, store: Any) -> None:
        self._store = store

    def get_state(self, canonical_id: str) -> Any:
        record = self._store.get(canonical_id)
        if record is None:
            return None
        return record.state


class _MemoryDecisionCloser:
    def __init__(self, store: Any) -> None:
        self._store = store

    def close(self, decision_ref: str | None, result: Any) -> None:
        if decision_ref is None:
            return
        try:
            cycle = int(decision_ref)
        except ValueError:
            return
        rec = self._store.get(cycle)
        if rec is None:
            return
        self._store.replace(
            DecisionRecord(
                cycle_number=rec.cycle_number,
                state="closed",
                opened_by=rec.opened_by,
                opened_at=rec.opened_at,
                closed_by="broker",
                observed_hash=rec.observed_hash,
                expected_outcome=rec.expected_outcome,
                capability=rec.capability,
                canonical_id=rec.canonical_id,
                request_json=rec.request_json,
                result_json=result.as_json(),
                actual_outcome=str(result.outcome),
                reason=rec.reason,
                alternatives=rec.alternatives,
                rationale=rec.rationale,
                decision=rec.decision,
            )
        )
