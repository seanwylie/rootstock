"""Phase 5 live: D1-D8, CloudTrail join on session name, cost per cycle."""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from rootstock.shared.identity import canonical_request_id
from rootstock.shared.vocabulary import SANDBOX_BUCKET_PREFIX
from tests.destructive import cases
from tests.destructive.cost import cycle_cost
from tests.destructive.runner import BY_ID, REGISTRY, destructively
from tests.fixtures import requests
from tests.live.helpers import cleanup_bucket, connect_live, invoke_lambda

pytestmark = pytest.mark.destructive

OPERATOR = "RootstockSandboxOperatorRole"


@pytest.mark.parametrize("spec_id", [spec.id for spec in REGISTRY])
def test_destructive_control(spec_id: str) -> None:
    spec = BY_ID[spec_id]
    assert spec.implementation is not None
    test = spec.implementation()
    try:
        with destructively(test):
            test.assert_correct_failure()
        if isinstance(test, cases.D2AlterConstitution):
            test.confirm_restored()
        if isinstance(test, cases.D8FailAuditClose):
            test.assert_reconciled()
    finally:
        if isinstance(test, cases.D8FailAuditClose):
            test.cleanup()


def test_cloudtrail_create_bucket_joins_decision() -> None:
    """Every Sandbox CreateBucket from the operator joins a claim by session name."""
    aws = connect_live()
    suffix = f"p5ct{uuid.uuid4().hex[:10]}"
    bucket = f"{SANDBOX_BUCKET_PREFIX}{suffix}"
    request = requests.create_bucket_request(
        suffix=suffix, purpose="phase5-cloudtrail", idempotency_key=suffix
    )
    cid = canonical_request_id(request)
    started = datetime.now(UTC) - timedelta(seconds=30)
    try:
        created = invoke_lambda(
            aws.core, str(aws.outputs["broker_function_name"]), request.as_json()
        )
        assert created["outcome"] == "SUCCESS", created
        assert created["canonical_id"] == cid
        event = _wait_create_bucket_event(aws.sandbox, bucket, started)
        session = _session_name(event)
        assert session == cid, {"session": session, "canonical_id": cid, "event": event}
        claim = (
            aws.core.resource("dynamodb")
            .Table("rootstock-claims")
            .get_item(Key={"canonical_id": cid}, ConsistentRead=True)
            .get("Item")
        )
        assert claim is not None
        assert str(claim["state"]) == "EXECUTED"

        window_start = datetime.now(UTC) - timedelta(minutes=20)
        orphans: list[str] = []
        for item in _lookup_create_buckets(aws.sandbox, window_start, datetime.now(UTC)):
            if OPERATOR not in _event_arn(item):
                continue
            name = _session_name(item)
            if name.startswith("reconcile"):
                continue
            row = (
                aws.core.resource("dynamodb")
                .Table("rootstock-claims")
                .get_item(Key={"canonical_id": name})
                .get("Item")
            )
            if row is None:
                orphans.append(name)
        assert orphans == [], f"CreateBucket session names with no claim: {orphans}"
    finally:
        cleanup_bucket(aws.sandbox.client("s3"), bucket)


def test_cost_per_cycle_is_known() -> None:
    aws = connect_live()
    suffix = f"p5c{uuid.uuid4().hex[:12]}"
    bucket = f"{SANDBOX_BUCKET_PREFIX}{suffix}"
    request = requests.create_bucket_request(
        suffix=suffix, purpose="phase5-cost", idempotency_key=suffix
    )
    t0 = datetime.now(UTC) - timedelta(seconds=15)
    try:
        for _ in range(3):
            noop = invoke_lambda(
                aws.core, str(aws.outputs["runtime_function_name"]), {"stub_mode": "noop"}
            )
            assert noop["action"] == "noop", noop
        created = invoke_lambda(
            aws.core, str(aws.outputs["broker_function_name"]), request.as_json()
        )
        assert created["outcome"] == "SUCCESS", created
        runtime_ms = _wait_duration(
            aws.core, str(aws.outputs["runtime_function_name"]), t0, min_samples=3
        )
        broker_ms = _wait_duration(
            aws.core, str(aws.outputs["broker_function_name"]), t0, min_samples=1
        )
        cost = cycle_cost(runtime_ms=runtime_ms, broker_ms=broker_ms, estimated_usd=0.0)
        assert cost.actual_usd > 0
        assert cost.actual_usd < 0.01
        assert cost.variance_usd == cost.actual_usd
        # Stable range: a cycle is two 256 MB Lambdas, each well under 30s.
        assert cost.duration_ms < 30_000
        print(
            f"cost_per_cycle usd={cost.actual_usd:.8f} "
            f"runtime_ms={runtime_ms} broker_ms={broker_ms} variance={cost.variance_usd:.8f}"
        )
    finally:
        cleanup_bucket(aws.sandbox.client("s3"), bucket)


def _lookup_create_buckets(session: Any, start: datetime, end: datetime) -> list[dict[str, Any]]:
    client = session.client("cloudtrail")
    events: list[dict[str, Any]] = []
    token: str | None = None
    while True:
        kwargs: dict[str, Any] = {
            "LookupAttributes": [{"AttributeKey": "EventName", "AttributeValue": "CreateBucket"}],
            "StartTime": start,
            "EndTime": end,
        }
        if token:
            kwargs["NextToken"] = token
        response = client.lookup_events(**kwargs)
        for raw in response.get("Events") or []:
            body = json.loads(str(raw.get("CloudTrailEvent") or "{}"))
            if isinstance(body, dict):
                events.append(body)
        token = response.get("NextToken")
        if not token:
            break
    return events


def _wait_create_bucket_event(
    session: Any, bucket: str, started: datetime, timeout: float = 180.0
) -> dict[str, Any]:
    deadline = time.time() + timeout
    last: list[dict[str, Any]] = []
    while time.time() < deadline:
        last = _lookup_create_buckets(session, started, datetime.now(UTC) + timedelta(minutes=1))
        for event in last:
            if bucket in json.dumps(event):
                return event
        time.sleep(10)
    raise AssertionError(f"no CreateBucket CloudTrail event for {bucket} (saw {len(last)} events)")


def _event_arn(event: dict[str, Any]) -> str:
    identity = event.get("userIdentity") or {}
    if isinstance(identity, dict):
        return str(identity.get("arn") or "")
    return ""


def _session_name(event: dict[str, Any]) -> str:
    arn = _event_arn(event)
    return arn.rsplit("/", 1)[-1] if "/" in arn else arn


def _wait_duration(
    session: Any, function_name: str, started: datetime, *, min_samples: int, timeout: float = 180.0
) -> int:
    cw = session.client("cloudwatch")
    deadline = time.time() + timeout
    last_count = 0.0
    last_avg = 0.0
    while time.time() < deadline:
        points = (
            cw.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Duration",
                Dimensions=[{"Name": "FunctionName", "Value": function_name}],
                StartTime=started,
                EndTime=datetime.now(UTC) + timedelta(minutes=1),
                Period=60,
                Statistics=["Average", "SampleCount"],
            ).get("Datapoints")
            or []
        )
        samples = sum(float(p.get("SampleCount") or 0) for p in points)
        if samples >= min_samples:
            # Weighted average across periods.
            total = sum(float(p["Average"]) * float(p["SampleCount"]) for p in points)
            return max(1, int(total / samples))
        last_count = samples
        last_avg = float(points[0]["Average"]) if points else 0.0
        time.sleep(10)
    raise AssertionError(
        f"Duration metric for {function_name} had {last_count} samples "
        f"(need {min_samples}); last avg={last_avg}"
    )
