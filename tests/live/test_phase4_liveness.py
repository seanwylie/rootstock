"""Phase 4 live: DLQ alarm, expired-lease metric, D1 silence, IAM cannot mute the monitor."""

from __future__ import annotations

import json
import time
from typing import Any

import pytest

from tests.live.helpers import invoke_lambda, tf_outputs

pytestmark = pytest.mark.live


def test_live_poison_reaches_dlq_and_alarm_exists() -> None:
    import boto3
    from check_aws_context import check_identity, load_accounts, resolve_profile

    accounts = load_accounts()
    check_identity(accounts, resolve_profile(accounts, "rootstock-core"), expect_zone="core")

    outputs = tf_outputs()
    core = boto3.Session(profile_name="rootstock-core", region_name="us-east-1")
    sqs = core.client("sqs")
    lam = core.client("lambda")
    cw = core.client("cloudwatch")
    queue = str(outputs["request_queue_url"])
    dlq = str(outputs["request_dlq_url"])
    mapping = lam.list_event_source_mappings(FunctionName=str(outputs["broker_function_name"]))[
        "EventSourceMappings"
    ][0]["UUID"]
    original = sqs.get_queue_attributes(
        QueueUrl=queue, AttributeNames=["VisibilityTimeout", "RedrivePolicy"]
    )["Attributes"]
    try:
        lam.update_event_source_mapping(UUID=mapping, Enabled=False)
        _wait_mapping(lam, mapping, enabled=False)
        time.sleep(2)
        from contextlib import suppress

        from botocore.exceptions import ClientError

        with suppress(ClientError):
            sqs.purge_queue(QueueUrl=queue)
            time.sleep(2)
        sqs.set_queue_attributes(
            QueueUrl=queue,
            Attributes={
                "VisibilityTimeout": "1",
                "RedrivePolicy": json.dumps(
                    {
                        "deadLetterTargetArn": _dlq_arn(dlq),
                        "maxReceiveCount": 1,
                    }
                ),
            },
        )
        sqs.send_message(QueueUrl=queue, MessageBody="not-json")
        # maxReceiveCount is compared on the *next* receive after a failed
        # delivery. One receive, let visibility expire, receive again → DLQ.
        first = sqs.receive_message(
            QueueUrl=queue, MaxNumberOfMessages=1, WaitTimeSeconds=10, VisibilityTimeout=1
        )
        if first.get("Messages"):
            time.sleep(1.5)
            sqs.receive_message(
                QueueUrl=queue, MaxNumberOfMessages=1, WaitTimeSeconds=5, VisibilityTimeout=1
            )
        _wait_dlq(sqs, dlq)
        alarm = cw.describe_alarms(AlarmNames=[str(outputs["dlq_alarm_name"])])["MetricAlarms"][0]
        assert alarm["Threshold"] == 1
        assert alarm["MetricName"] == "ApproximateNumberOfMessagesVisible"
        _wait_alarm(cw, str(outputs["dlq_alarm_name"]))
    finally:
        sqs.set_queue_attributes(
            QueueUrl=queue,
            Attributes={
                "VisibilityTimeout": original["VisibilityTimeout"],
                "RedrivePolicy": original["RedrivePolicy"],
            },
        )
        _drain(sqs, dlq)
        _drain(sqs, queue)
        lam.update_event_source_mapping(UUID=mapping, Enabled=True)
        _wait_mapping(lam, mapping, enabled=True)


def test_live_expired_lease_metric_and_cannot_mute_monitor() -> None:
    import boto3
    from check_aws_context import check_identity, load_accounts, resolve_profile

    accounts = load_accounts()
    check_identity(accounts, resolve_profile(accounts, "rootstock-core"), expect_zone="core")

    outputs = tf_outputs()
    core = boto3.Session(profile_name="rootstock-core", region_name="us-east-1")
    cw = core.client("cloudwatch")
    alarm = cw.describe_alarms(AlarmNames=[str(outputs["expired_lease_alarm_name"])])[
        "MetricAlarms"
    ]
    assert alarm and alarm[0]["MetricName"] == "ExpiredLease"

    iam = core.client("iam")
    runtime = str(outputs["runtime_role_arn"])
    account = str(outputs["core_account_id"])
    region = "us-east-1"
    for action, resource, label in (
        (
            "events:DisableRule",
            f"arn:aws:events:{region}:{account}:rule/{outputs['silence_watch_rule_name']}",
            "runtime cannot disable silence watch",
        ),
        (
            "cloudwatch:DeleteAlarms",
            f"arn:aws:cloudwatch:{region}:{account}:alarm:{outputs['heartbeat_silence_alarm_name']}",
            "runtime cannot delete silence alarm",
        ),
        (
            "cloudwatch:DisableAlarmActions",
            f"arn:aws:cloudwatch:{region}:{account}:alarm:{outputs['heartbeat_silence_alarm_name']}",
            "runtime cannot disable silence alarm actions",
        ),
        (
            "lambda:UpdateFunctionConfiguration",
            f"arn:aws:lambda:{region}:{account}:function:{outputs['runtime_function_name']}",
            "runtime cannot change HEARTBEAT_URL",
        ),
        (
            "lambda:DeleteFunction",
            f"arn:aws:lambda:{region}:{account}:function:{outputs['heartbeat_sink_function_name']}",
            "runtime cannot delete heartbeat sink",
        ),
        (
            "dynamodb:PutItem",
            f"arn:aws:dynamodb:{region}:{account}:table/{outputs['heartbeat_table']}",
            "runtime cannot fake last_ping",
        ),
        (
            "ssm:PutParameter",
            f"arn:aws:ssm:{region}:{account}:parameter{outputs['heartbeat_silence_param']}",
            "runtime cannot extend the silence window",
        ),
    ):
        decision = iam.simulate_principal_policy(
            PolicySourceArn=runtime,
            ActionNames=[action],
            ResourceArns=[resource],
        )["EvaluationResults"][0]["EvalDecision"]
        assert decision.lower() != "allowed", f"{label}: {action} was {decision}"


def test_live_d1_kill_runtime_silence_alerts() -> None:
    import boto3
    from check_aws_context import check_identity, load_accounts, resolve_profile

    accounts = load_accounts()
    check_identity(accounts, resolve_profile(accounts, "rootstock-core"), expect_zone="core")

    outputs = tf_outputs()
    core = boto3.Session(profile_name="rootstock-core", region_name="us-east-1")
    lam = core.client("lambda")
    ssm = core.client("ssm")
    table = core.resource("dynamodb").Table(str(outputs["heartbeat_table"]))
    param = str(outputs["heartbeat_silence_param"])
    original_window = ssm.get_parameter(Name=param)["Parameter"]["Value"]
    runtime_name = str(outputs["runtime_function_name"])
    watch_name = str(outputs["silence_watch_function_name"])
    try:
        ssm.put_parameter(Name=param, Value="5", Type="String", Overwrite=True)
        pinged = invoke_lambda(core, runtime_name, {"stub_mode": "noop"})
        assert pinged["action"] == "noop", pinged
        last = table.get_item(Key={"pk": "monitor", "sk": "last"}, ConsistentRead=True).get("Item")
        assert last is not None and int(str(last["last_ping"])) > 0
        lam.put_function_concurrency(FunctionName=runtime_name, ReservedConcurrentExecutions=0)
        time.sleep(6)
        watched: dict[str, Any] | None = None
        last_error: Exception | None = None
        for _ in range(3):
            try:
                watched = invoke_lambda(core, watch_name, {})
                break
            except AssertionError as exc:
                last_error = exc
                time.sleep(2)
        if watched is None:
            raise AssertionError(last_error)
        assert watched["silent"] is True, watched
        assert int(watched["age"] or 0) >= 5
    finally:
        from contextlib import suppress

        from botocore.exceptions import ClientError

        with suppress(ClientError):
            lam.delete_function_concurrency(FunctionName=runtime_name)
        ssm.put_parameter(Name=param, Value=original_window, Type="String", Overwrite=True)
        invoke_lambda(core, runtime_name, {"stub_mode": "noop"})
        invoke_lambda(core, watch_name, {})


def _dlq_arn(url: str) -> str:
    # https://sqs.us-east-1.amazonaws.com/ACCOUNT/name
    parts = url.rsplit("/", 2)
    return f"arn:aws:sqs:us-east-1:{parts[-2]}:{parts[-1]}"


def _wait_dlq(sqs: Any, url: str, timeout: float = 45.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        got = sqs.receive_message(
            QueueUrl=url, MaxNumberOfMessages=1, WaitTimeSeconds=2, VisibilityTimeout=5
        )
        if got.get("Messages"):
            return
        attrs = sqs.get_queue_attributes(
            QueueUrl=url, AttributeNames=["ApproximateNumberOfMessages"]
        )["Attributes"]
        if int(attrs.get("ApproximateNumberOfMessages") or 0) > 0:
            return
        time.sleep(1)
    raise AssertionError("poison message never reached the DLQ")


def _wait_mapping(lam: Any, mapping_uuid: str, *, enabled: bool, timeout: float = 45.0) -> None:
    want = "Enabled" if enabled else "Disabled"
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = str(lam.get_event_source_mapping(UUID=mapping_uuid).get("State") or "")
        if state == want:
            return
        time.sleep(1)
    raise AssertionError(f"event source mapping did not become {want}")


def _wait_alarm(cw: Any, name: str, timeout: float = 180.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        alarm = cw.describe_alarms(AlarmNames=[name])["MetricAlarms"][0]
        if alarm["StateValue"] == "ALARM":
            return
        time.sleep(10)
    raise AssertionError(f"alarm {name} did not enter ALARM")


def _drain(sqs: Any, url: str) -> None:
    for _ in range(10):
        response = sqs.receive_message(
            QueueUrl=url, MaxNumberOfMessages=10, WaitTimeSeconds=1, VisibilityTimeout=5
        )
        messages = response.get("Messages") or []
        if not messages:
            return
        for message in messages:
            sqs.delete_message(QueueUrl=url, ReceiptHandle=message["ReceiptHandle"])
