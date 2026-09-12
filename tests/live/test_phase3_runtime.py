"""Phase 3 live: runtime Lambda → SQS → broker Lambda, ten cycles."""

from __future__ import annotations

import time
from typing import Any

import pytest

from rootstock.shared.vocabulary import SANDBOX_BUCKET_PREFIX
from tests.live.helpers import invoke_lambda, tf_outputs

pytestmark = pytest.mark.live

TEN = 10


def test_live_runtime_loop() -> None:
    import boto3
    from check_aws_context import check_identity, load_accounts, resolve_profile

    accounts = load_accounts()
    check_identity(accounts, resolve_profile(accounts, "rootstock-core"), expect_zone="core")
    check_identity(accounts, resolve_profile(accounts, "rootstock-sandbox"), expect_zone="sandbox")

    outputs = tf_outputs()
    core = boto3.Session(profile_name="rootstock-core", region_name="us-east-1")
    sandbox = boto3.Session(profile_name="rootstock-sandbox", region_name="us-east-1")
    decisions = core.resource("dynamodb").Table("rootstock-decisions")
    s3 = sandbox.client("s3")
    created: list[str] = []
    cycles: list[dict[str, Any]] = []
    try:
        for _ in range(TEN):
            result = invoke_lambda(core, outputs["runtime_function_name"], {})
            assert result["action"] == "enqueued", result
            _wait_closed(decisions, int(result["cycle_number"]))
            cycles.append(result)
            created.append(f"{SANDBOX_BUCKET_PREFIX}cycle-{result['cycle_number']}")
            s3.head_bucket(Bucket=created[-1])

        assert len(cycles) == TEN
        second = cycles[1]
        assert second["expected_outcome_met"] is True

        first_item = decisions.get_item(Key={"cycle_number": int(cycles[0]["cycle_number"])})[
            "Item"
        ]
        assert first_item["opened_by"] == "runtime"
        assert first_item["closed_by"] == "broker"

        noop = invoke_lambda(core, outputs["runtime_function_name"], {"stub_mode": "noop"})
        assert noop["action"] == "noop"
        noop_item = decisions.get_item(Key={"cycle_number": int(noop["cycle_number"])})["Item"]
        assert noop_item["opened_by"] == "runtime"
        assert noop_item["closed_by"] == "runtime"
        assert noop_item["state"] == "closed"
    finally:
        for bucket in created:
            _cleanup_bucket(s3, bucket)


def test_live_runtime_skip_and_halt() -> None:
    import boto3
    from check_aws_context import check_identity, load_accounts, resolve_profile

    accounts = load_accounts()
    check_identity(accounts, resolve_profile(accounts, "rootstock-core"), expect_zone="core")
    check_identity(accounts, resolve_profile(accounts, "rootstock-sandbox"), expect_zone="sandbox")

    outputs = tf_outputs()
    core = boto3.Session(profile_name="rootstock-core", region_name="us-east-1")
    lam = core.client("lambda")
    broker_name = str(outputs["broker_function_name"])
    mapping_uuid = _broker_mapping(lam, broker_name)
    decisions = core.resource("dynamodb").Table("rootstock-decisions")
    memory = core.resource("dynamodb").Table("rootstock-memory")
    claims = core.resource("dynamodb").Table("rootstock-claims")
    sandbox = boto3.Session(profile_name="rootstock-sandbox", region_name="us-east-1").client("s3")
    queue_url = str(outputs["request_queue_url"])
    bucket: str | None = None
    halted_cycle: int | None = None
    paused = False
    try:
        # Disabled mapping still delivers at-least-once SQS messages. Throttle
        # the broker Lambda to zero so it cannot close the prior decision.
        _pause_broker(lam, broker_name, mapping_uuid)
        paused = True
        _drain_queue(core, queue_url)
        _park_past_open_prior(decisions, memory)

        first = invoke_lambda(core, outputs["runtime_function_name"], {})
        assert first["action"] == "enqueued", first
        assert first.get("canonical_id"), first
        bucket = f"{SANDBOX_BUCKET_PREFIX}cycle-{first['cycle_number']}"
        _drain_queue(core, queue_url)
        _assert_open(decisions, int(first["cycle_number"]))

        skipped = invoke_lambda(core, outputs["runtime_function_name"], {})
        assert skipped["action"] == "skipped", skipped
        _assert_open(decisions, int(first["cycle_number"]))

        claims.put_item(
            Item={
                "canonical_id": str(first["canonical_id"]),
                "state": "PENDING",
                "lease_expires_at": int(time.time()) - 60,
                "attempt": 1,
                "incident": False,
            }
        )
        halted = invoke_lambda(core, outputs["runtime_function_name"], {})
        assert halted["action"] == "halted", halted
        assert halted["reason"] == "prior_lease_expired"
        halted_cycle = int(halted["cycle_number"])
    finally:
        _drain_queue(core, queue_url)
        if paused:
            _resume_broker(lam, broker_name, mapping_uuid)
        if halted_cycle is not None:
            memory.put_item(Item={"pk": "runtime", "sk": "cursor", "next_cycle": halted_cycle + 1})
        if bucket:
            _cleanup_bucket(sandbox, bucket)


def _park_past_open_prior(decisions: Any, memory: Any) -> None:
    """Advance the cursor if the previous decision is still open.

    Failed skip/halt runs leave an open decision at cursor-1. The next enqueue
    would skip instead of creating a fresh in-flight prior.
    """
    item = memory.get_item(Key={"pk": "runtime", "sk": "cursor"}).get("Item")
    nxt = int(item["next_cycle"]) if item else 1
    while nxt > 1:
        prior = decisions.get_item(Key={"cycle_number": nxt - 1}, ConsistentRead=True).get("Item")
        if prior is None or str(prior.get("state")) != "open":
            break
        nxt += 1
        memory.put_item(Item={"pk": "runtime", "sk": "cursor", "next_cycle": nxt})


def _pause_broker(lam: Any, function_name: str, mapping_uuid: str) -> None:
    lam.put_function_concurrency(FunctionName=function_name, ReservedConcurrentExecutions=0)
    lam.update_event_source_mapping(UUID=mapping_uuid, Enabled=False)
    _wait_mapping(lam, mapping_uuid, enabled=False)
    time.sleep(2)


def _resume_broker(lam: Any, function_name: str, mapping_uuid: str) -> None:
    from contextlib import suppress

    from botocore.exceptions import ClientError

    with suppress(ClientError):
        lam.delete_function_concurrency(FunctionName=function_name)
    lam.update_event_source_mapping(UUID=mapping_uuid, Enabled=True)
    _wait_mapping(lam, mapping_uuid, enabled=True)


def _assert_open(table: Any, cycle: int) -> None:
    item = table.get_item(Key={"cycle_number": cycle}, ConsistentRead=True).get("Item")
    assert item is not None and str(item.get("state")) == "open", item


def _wait_closed(table: Any, cycle: int, timeout: float = 45.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        item = table.get_item(Key={"cycle_number": cycle}).get("Item")
        if item and str(item.get("state")) == "closed" and item.get("closed_by") == "broker":
            assert isinstance(item, dict)
            return item
        time.sleep(0.5)
    raise AssertionError(f"decision {cycle} did not close")


def _wait_mapping(lam: Any, mapping_uuid: str, *, enabled: bool, timeout: float = 45.0) -> None:
    want = "Enabled" if enabled else "Disabled"
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = str(lam.get_event_source_mapping(UUID=mapping_uuid).get("State") or "")
        if state == want:
            return
        time.sleep(1)
    raise AssertionError(f"event source mapping did not become {want}")


def _broker_mapping(lam: Any, function_name: str) -> str:
    mappings = lam.list_event_source_mappings(FunctionName=function_name)["EventSourceMappings"]
    assert mappings, "broker SQS mapping missing"
    return str(mappings[0]["UUID"])


def _drain_queue(session: Any, url: str) -> None:
    sqs = session.client("sqs")
    for _ in range(10):
        response = sqs.receive_message(
            QueueUrl=url, MaxNumberOfMessages=10, WaitTimeSeconds=1, VisibilityTimeout=30
        )
        messages = response.get("Messages") or []
        if not messages:
            return
        for message in messages:
            sqs.delete_message(QueueUrl=url, ReceiptHandle=message["ReceiptHandle"])


def _cleanup_bucket(s3: Any, bucket: str) -> None:
    from contextlib import suppress

    from botocore.exceptions import ClientError

    with suppress(ClientError):
        s3.delete_bucket(Bucket=bucket)
