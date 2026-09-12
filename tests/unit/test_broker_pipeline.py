"""Phase 2 broker pipeline: the eight exit criteria, in-process."""

from __future__ import annotations

from rootstock.broker.executor import FakeExecutor
from rootstock.broker.pipeline import in_memory_broker
from rootstock.broker.stores import FrozenClock, MemoryAudit, MemoryClaimStore
from rootstock.shared.capability import Outcome
from rootstock.shared.claims import ClaimState
from rootstock.shared.identity import canonical_request_id
from rootstock.shared.vocabulary import SANDBOX_BUCKET_PREFIX
from tests.fixtures import requests


def test_canonical_id_is_stable_and_content_sensitive() -> None:
    a = requests.create_bucket_request(idempotency_key="1", suffix="abc")
    b = requests.create_bucket_request(idempotency_key="1", suffix="abc")
    c = requests.create_bucket_request(idempotency_key="1", suffix="abd")
    d = requests.create_bucket_request(idempotency_key="2", suffix="abc")
    assert canonical_request_id(a) == canonical_request_id(b)
    assert canonical_request_id(a) != canonical_request_id(c)
    assert canonical_request_id(a) != canonical_request_id(d)
    assert len(canonical_request_id(a)) == 64


def test_happy_path_creates_tagged_bucket() -> None:
    executor = FakeExecutor()
    broker = in_memory_broker(executor=executor)
    request = requests.create_bucket_request(suffix="phase2ok")
    result = broker.process(request)
    assert result.outcome is Outcome.SUCCESS
    name = f"{SANDBOX_BUCKET_PREFIX}phase2ok"
    assert name in executor.buckets
    assert executor.tags[name]["rootstock:managed-by"] == "rootstock"
    assert executor.tags[name]["rootstock:purpose"] == "fixture"
    assert executor.calls == 1


def test_replay_is_duplicate_and_does_not_execute_again() -> None:
    executor = FakeExecutor()
    audit = MemoryAudit()
    broker = in_memory_broker(executor=executor, audit=audit)
    request = requests.create_bucket_request(suffix="phase2replay")
    first = broker.process(request)
    second = broker.process(request)
    assert first.outcome is Outcome.SUCCESS
    assert second.outcome is Outcome.DUPLICATE
    assert executor.calls == 1
    assert len(audit.opens) == 1
    assert len(audit.closes) == 1
    assert second.audit_id == first.audit_id


def test_undeclared_capability_is_rejected_before_policy() -> None:
    executor = FakeExecutor()
    broker = in_memory_broker(executor=executor)
    result = broker.process(requests.undeclared_capability_request())
    assert result.outcome is Outcome.REJECTED
    assert result.rule == "schema.undeclared_capability"
    assert executor.calls == 0
    claims = broker.claims
    assert isinstance(claims, MemoryClaimStore)
    assert claims.rows == {}


def test_malformed_parameters_are_rejected() -> None:
    broker = in_memory_broker()
    result = broker.process(requests.malformed_request())
    assert result.outcome is Outcome.REJECTED
    assert result.rule == "schema.parameters"


def test_out_of_scope_is_denied_with_named_rule() -> None:
    executor = FakeExecutor()
    broker = in_memory_broker(executor=executor)
    result = broker.process(requests.out_of_scope_request())
    assert result.outcome is Outcome.DENIED
    assert result.rule == "scope.target"
    assert executor.calls == 0


def test_audit_open_failure_blocks_execution() -> None:
    executor = FakeExecutor()
    audit = MemoryAudit(fail_open=True)
    broker = in_memory_broker(executor=executor, audit=audit)
    result = broker.process(requests.create_bucket_request(suffix="phase2d7"))
    assert result.outcome is Outcome.FAILURE
    assert result.rule == "audit.open"
    assert executor.calls == 0
    assert executor.buckets == set()


def test_audit_close_failure_is_unknown_not_failure() -> None:
    executor = FakeExecutor()
    audit = MemoryAudit(fail_close=True)
    broker = in_memory_broker(executor=executor, audit=audit)
    request = requests.create_bucket_request(suffix="phase2d8")
    result = broker.process(request)
    assert result.outcome is Outcome.UNKNOWN
    assert executor.calls == 1
    assert f"{SANDBOX_BUCKET_PREFIX}phase2d8" in executor.buckets
    record = broker.claims.get(canonical_request_id(request))
    assert record is not None
    assert record.state is ClaimState.UNKNOWN
    assert record.incident is True
    from rootstock.broker.stores import MemoryIncidents

    incidents = broker.incidents
    assert isinstance(incidents, MemoryIncidents)
    assert incidents.events


def test_reconciliation_closes_unknown_from_provider() -> None:
    executor = FakeExecutor()
    audit = MemoryAudit(fail_close=True)
    broker = in_memory_broker(executor=executor, audit=audit)
    request = requests.create_bucket_request(suffix="phase2recon")
    first = broker.process(request)
    assert first.outcome is Outcome.UNKNOWN
    audit.fail_close = False
    second = broker.process(request)
    assert second.outcome is Outcome.SUCCESS
    assert second.rule == "reconcile.provider"
    assert executor.calls == 1
    record = broker.claims.get(canonical_request_id(request))
    assert record is not None
    assert record.state is ClaimState.EXECUTED


def test_session_policy_is_narrower_than_role_ceiling() -> None:
    executor = FakeExecutor()
    broker = in_memory_broker(executor=executor)
    broker.process(requests.create_bucket_request(suffix="phase2sess"))
    policy = executor.last_session_policy()
    assert policy is not None
    actions: set[str] = set()
    resources: set[str] = set()
    for statement in policy["Statement"]:
        actions.update(statement["Action"])
        resource = statement["Resource"]
        if isinstance(resource, list):
            resources.update(resource)
        else:
            resources.add(resource)
    assert actions == {"s3:CreateBucket", "s3:PutBucketTagging", "s3:ListBucket"}
    assert resources == {f"arn:aws:s3:::{SANDBOX_BUCKET_PREFIX}phase2sess"}
    assert "s3:PutObject" not in actions
    assert "logs:DescribeLogGroups" not in actions


def test_in_flight_pending_is_duplicate() -> None:
    executor = FakeExecutor()
    clock = FrozenClock(1_000_000)
    broker = in_memory_broker(executor=executor, clock=clock)
    request = requests.create_bucket_request(suffix="phase2lease")
    first = broker.process(request)
    assert first.outcome is Outcome.SUCCESS
    # Force the claim back to a live lease without executing.
    record = broker.claims.get(canonical_request_id(request))
    assert record is not None
    record.state = ClaimState.PENDING
    record.lease_expires_at = int(clock.now()) + 60
    broker.claims.save(record)
    second = broker.process(request)
    assert second.outcome is Outcome.DUPLICATE
    assert executor.calls == 1
