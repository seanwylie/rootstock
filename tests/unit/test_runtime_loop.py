"""Phase 3 runtime loop: the six exit criteria, in-process."""

from __future__ import annotations

from pathlib import Path

from rootstock.broker.stores import LEASE_SECONDS, ClaimRecord, FrozenClock
from rootstock.runtime.loop import filesystem_constitution, in_memory_runtime
from rootstock.runtime.memory import CLAIM_FIELDS, NOOP_EXPECTED
from rootstock.runtime.reasoner import StubMode, StubReasoner
from rootstock.shared.claims import ClaimState
from rootstock.shared.vocabulary import SANDBOX_BUCKET_PREFIX


def test_ten_consecutive_cycles_create_buckets() -> None:
    _, harness = in_memory_runtime()
    for _ in range(10):
        result = harness.wake_and_drain()
        assert result.action == "enqueued"
    assert harness.executor.calls == 10
    assert len(harness.executor.buckets) == 10


def test_next_cycle_observes_prior_bucket() -> None:
    _, harness = in_memory_runtime()
    first = harness.wake_and_drain()
    second = harness.wake_and_drain()
    assert first.expected_outcome_met is None
    assert second.expected_outcome_met is True
    bucket = f"{SANDBOX_BUCKET_PREFIX}cycle-{first.cycle_number}"
    assert bucket in harness.executor.buckets
    prior = harness.decisions.get(first.cycle_number)
    assert prior is not None
    assert prior.actual_outcome == "SUCCESS"


def test_noop_still_writes_a_decision() -> None:
    _, harness = in_memory_runtime(reasoner=StubReasoner(StubMode.NOOP))
    result = harness.wake_and_drain()
    assert result.action == "noop"
    record = harness.decisions.get(result.cycle_number)
    assert record is not None
    assert record.state == "closed"
    assert record.opened_by == "runtime"
    assert record.closed_by == "runtime"
    assert record.actual_outcome == "no_action"
    assert record.expected_outcome == NOOP_EXPECTED
    assert harness.executor.calls == 0
    assert harness.memory.wakes[-1]["outcome"] == "cycle"


def test_runtime_source_never_assumes_a_role() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "rootstock" / "runtime"
    for path in root.rglob("*.py"):
        for line in path.read_text().splitlines():
            if "assume_role(" in line.split("#", 1)[0]:
                raise AssertionError(f"{path} calls assume_role: {line}")


def test_valid_lease_skips_and_expired_lease_halts() -> None:
    clock = FrozenClock(1_000_000)
    _, harness = in_memory_runtime(clock=clock)
    first = harness.wake()
    assert first.action == "enqueued"
    skipped = harness.wake()
    assert skipped.action == "skipped"
    assert harness.decisions.get(skipped.cycle_number) is None
    assert harness.cursor.get().next_cycle == first.cycle_number + 1
    assert harness.memory.wakes[-1]["outcome"] == "skip"
    assert harness.memory.wakes[-1]["cycle_number"] is None
    clock.t = 1_000_000 + LEASE_SECONDS + 1
    halted = harness.wake()
    assert halted.action == "halted"
    assert halted.reason == "prior_lease_expired"
    assert harness.memory.wakes[-1]["outcome"] == "halt"


def test_learn_writes_the_claim_schema() -> None:
    _, harness = in_memory_runtime()
    harness.wake_and_drain()
    harness.wake_and_drain()
    claim = harness.memory.items[0]
    for field in CLAIM_FIELDS:
        assert field in claim, field
    assert "kind" not in claim
    assert claim["status"] == "active"
    assert claim["evidence"]["expected_outcome_met"] is True


def test_pending_claim_with_valid_lease_skips() -> None:
    clock = FrozenClock(1_000_000)
    _, harness = in_memory_runtime(clock=clock)
    first = harness.wake()
    record = harness.decisions.get(first.cycle_number)
    assert record is not None and record.canonical_id
    harness.claims.save(
        ClaimRecord(
            canonical_id=record.canonical_id,
            state=ClaimState.PENDING,
            lease_expires_at=1_000_000 + 60,
            attempt=1,
        )
    )
    skipped = harness.wake()
    assert skipped.action == "skipped"


def test_expired_pending_claim_halts() -> None:
    clock = FrozenClock(1_000_000)
    _, harness = in_memory_runtime(clock=clock)
    first = harness.wake()
    record = harness.decisions.get(first.cycle_number)
    assert record is not None and record.canonical_id
    harness.claims.save(
        ClaimRecord(
            canonical_id=record.canonical_id,
            state=ClaimState.PENDING,
            lease_expires_at=1_000_000 - 1,
            attempt=1,
        )
    )
    halted = harness.wake()
    assert halted.action == "halted"


def test_decision_has_two_authors() -> None:
    _, harness = in_memory_runtime()
    result = harness.wake_and_drain()
    record = harness.decisions.get(result.cycle_number)
    assert record is not None
    assert record.opened_by == "runtime"
    assert record.closed_by == "broker"
    assert record.state == "closed"


def test_bad_constitution_digest_halts_before_enqueue() -> None:
    constitution = filesystem_constitution()
    constitution.expected_digest = "0" * 64
    _, harness = in_memory_runtime(constitution=constitution)
    result = harness.wake()
    assert result.action == "halted"
    assert result.reason == "constitution_digest_mismatch"
    assert harness.executor.calls == 0
    assert harness.queue.messages == []
