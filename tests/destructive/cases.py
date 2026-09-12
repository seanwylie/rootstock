"""Live D1-D8 bodies. Each breaks something, asserts the correct failure, then restores."""

from __future__ import annotations

import json
import time
import uuid
from contextlib import suppress
from typing import Any

from botocore.exceptions import ClientError

from rootstock.shared.identity import canonical_request_id
from rootstock.shared.vocabulary import SANDBOX_BUCKET_PREFIX
from tests.destructive.runner import DestructiveTest
from tests.fixtures import requests
from tests.live.helpers import (
    LiveAws,
    cleanup_bucket,
    connect_live,
    invoke_lambda,
    simulate,
)

D7_POLICY = "phase5-d7-deny-audit-open"
D8_POLICY = "phase5-d8-deny-audit-close"
BROKER_ROLE = "rootstock-broker-role"


def _clear_audit_bucket_policy(aws: LiveAws) -> None:
    s3 = aws.core.client("s3")
    with suppress(ClientError):
        s3.delete_bucket_policy(Bucket=str(aws.outputs["audit_bucket"]))


def _deny_audit_put(aws: LiveAws, resources: list[str], sid: str) -> None:
    _clear_audit_bucket_policy(aws)
    aws.core.client("s3").put_bucket_policy(
        Bucket=str(aws.outputs["audit_bucket"]),
        Policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": sid,
                        "Effect": "Deny",
                        "Principal": {"AWS": str(aws.outputs["broker_role_arn"])},
                        "Action": "s3:PutObject",
                        "Resource": resources,
                    }
                ],
            }
        ),
    )


def _broker(aws: LiveAws, payload: dict[str, Any]) -> dict[str, Any]:
    return invoke_lambda(aws.core, str(aws.outputs["broker_function_name"]), payload)


def _runtime(aws: LiveAws, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return invoke_lambda(aws.core, str(aws.outputs["runtime_function_name"]), payload or {})


def _delete_role_policy(iam: Any, name: str) -> None:
    with suppress(ClientError):
        iam.delete_role_policy(RoleName=BROKER_ROLE, PolicyName=name)


class D1KillRuntime:
    """Kill the runtime (reserved concurrency 0) and observe silence."""

    def __init__(self) -> None:
        self._aws = connect_live()
        self._original_window = ""

    def break_it(self) -> None:
        aws = self._aws
        ssm = aws.core.client("ssm")
        param = str(aws.outputs["heartbeat_silence_param"])
        self._original_window = ssm.get_parameter(Name=param)["Parameter"]["Value"]
        ssm.put_parameter(Name=param, Value="5", Type="String", Overwrite=True)
        pinged = _runtime(aws, {"stub_mode": "noop"})
        assert pinged["action"] == "noop", pinged
        aws.core.client("lambda").put_function_concurrency(
            FunctionName=str(aws.outputs["runtime_function_name"]),
            ReservedConcurrentExecutions=0,
        )

    def assert_correct_failure(self) -> None:
        time.sleep(6)
        watched: dict[str, Any] | None = None
        last_error: Exception | None = None
        for _ in range(3):
            try:
                watched = invoke_lambda(
                    self._aws.core, str(self._aws.outputs["silence_watch_function_name"]), {}
                )
                break
            except AssertionError as exc:
                last_error = exc
                time.sleep(2)
        if watched is None:
            raise AssertionError(last_error)
        assert watched["silent"] is True, watched
        assert int(watched["age"] or 0) >= 5

    def restore(self) -> None:
        aws = self._aws
        lam = aws.core.client("lambda")
        runtime_name = str(aws.outputs["runtime_function_name"])
        with suppress(ClientError):
            lam.delete_function_concurrency(FunctionName=runtime_name)
        if self._original_window:
            aws.core.client("ssm").put_parameter(
                Name=str(aws.outputs["heartbeat_silence_param"]),
                Value=self._original_window,
                Type="String",
                Overwrite=True,
            )
        _runtime(aws, {"stub_mode": "noop"})
        invoke_lambda(aws.core, str(aws.outputs["silence_watch_function_name"]), {})


class D2AlterConstitution:
    """Overwrite constitution.json so VERIFY's digest check fails closed."""

    def __init__(self) -> None:
        self._aws = connect_live()
        self._original: bytes | None = None

    def break_it(self) -> None:
        s3 = self._aws.core.client("s3")
        bucket = str(self._aws.outputs["grant_bucket"])
        self._original = s3.get_object(Bucket=bucket, Key="constitution.json")["Body"].read()
        s3.put_object(
            Bucket=bucket,
            Key="constitution.json",
            Body=b'{"tampered":true,"runtime_write":true}\n',
            ContentType="application/json",
        )

    def assert_correct_failure(self) -> None:
        result = _runtime(self._aws, {})
        assert result["action"] == "halted", result
        assert result["reason"] == "constitution_digest_mismatch", result

    def restore(self) -> None:
        if self._original is None:
            return
        self._aws.core.client("s3").put_object(
            Bucket=str(self._aws.outputs["grant_bucket"]),
            Key="constitution.json",
            Body=self._original,
            ContentType="application/json",
        )

    def confirm_restored(self) -> None:
        result = _runtime(self._aws, {"stub_mode": "noop"})
        if result["action"] == "halted":
            assert result["reason"] != "constitution_digest_mismatch", result


class D3RuntimeCannotAssume:
    """The runtime has no sts:AssumeRole, so it cannot invoke a capability itself."""

    def __init__(self) -> None:
        self._aws = connect_live()

    def break_it(self) -> None:
        return

    def assert_correct_failure(self) -> None:
        runtime = str(self._aws.outputs["runtime_role_arn"])
        operator = str(self._aws.outputs["sandbox_operator_role_arn"])
        management = "arn:aws:iam::000000000000:role/RootstockManagement"
        for action, resource, label in (
            ("sts:AssumeRole", operator, "sandbox operator"),
            ("sts:AssumeRole", management, "management-shaped role"),
        ):
            decision = simulate(self._aws.core, runtime, action, resource)
            assert decision.lower() != "allowed", f"{label}: {action} was {decision}"

    def restore(self) -> None:
        return


class D4Replay:
    """Identical request: one side effect, second result DUPLICATE."""

    def __init__(self) -> None:
        self._aws = connect_live()
        self._suffix = f"d4{uuid.uuid4().hex[:12]}"
        self._bucket = f"{SANDBOX_BUCKET_PREFIX}{self._suffix}"
        self._request = requests.create_bucket_request(
            suffix=self._suffix, purpose="phase5-d4", idempotency_key=self._suffix
        )
        self._first: dict[str, Any] | None = None

    def break_it(self) -> None:
        first = _broker(self._aws, self._request.as_json())
        assert first["outcome"] == "SUCCESS", first
        self._first = first
        self._aws.sandbox.client("s3").head_bucket(Bucket=self._bucket)

    def assert_correct_failure(self) -> None:
        assert self._first is not None
        second = _broker(self._aws, self._request.as_json())
        assert second["outcome"] == "DUPLICATE", second
        assert second["audit_id"] == self._first["audit_id"]
        self._aws.sandbox.client("s3").head_bucket(Bucket=self._bucket)

    def restore(self) -> None:
        cleanup_bucket(self._aws.sandbox.client("s3"), self._bucket)


class D5Undeclared:
    def __init__(self) -> None:
        self._aws = connect_live()

    def break_it(self) -> None:
        return

    def assert_correct_failure(self) -> None:
        result = _broker(
            self._aws,
            requests.undeclared_capability_request(idempotency_key=uuid.uuid4().hex[:12]).as_json(),
        )
        assert result["outcome"] == "REJECTED", result
        assert result["rule"] == "schema.undeclared_capability"

    def restore(self) -> None:
        return


class D6OutOfScope:
    def __init__(self) -> None:
        self._aws = connect_live()

    def break_it(self) -> None:
        return

    def assert_correct_failure(self) -> None:
        result = _broker(
            self._aws,
            requests.out_of_scope_request(idempotency_key=uuid.uuid4().hex[:12]).as_json(),
        )
        assert result["outcome"] == "DENIED", result
        assert result["rule"] == "scope.target"

    def restore(self) -> None:
        return


class D7RevokeAuditOpen:
    """Deny broker PutObject on the audit bucket so AUDIT OPEN fails closed."""

    def __init__(self) -> None:
        self._aws = connect_live()
        self._bucket = ""
        self._audit_objects = f"arn:aws:s3:::{self._aws.outputs['audit_bucket']}/*"

    def break_it(self) -> None:
        _delete_role_policy(self._aws.core.client("iam"), D7_POLICY)
        _deny_audit_put(self._aws, [self._audit_objects], "Phase5D7DenyAuditOpen")
        time.sleep(1)

    def assert_correct_failure(self) -> None:
        result: dict[str, Any] | None = None
        for _ in range(12):
            suffix = f"d7{uuid.uuid4().hex[:12]}"
            bucket = f"{SANDBOX_BUCKET_PREFIX}{suffix}"
            request = requests.create_bucket_request(
                suffix=suffix, purpose="phase5-d7", idempotency_key=suffix
            )
            result = _broker(self._aws, request.as_json())
            if result["outcome"] == "FAILURE" and result.get("rule") == "audit.open":
                self._bucket = bucket
                with suppress(ClientError):
                    self._aws.sandbox.client("s3").head_bucket(Bucket=bucket)
                    raise AssertionError(f"bucket {bucket} was created despite AUDIT OPEN failure")
                return
            if result["outcome"] == "SUCCESS":
                cleanup_bucket(self._aws.sandbox.client("s3"), bucket)
            time.sleep(2)
        assert result is not None
        raise AssertionError(f"AUDIT OPEN deny never took effect: {result}")

    def restore(self) -> None:
        _clear_audit_bucket_policy(self._aws)
        _delete_role_policy(self._aws.core.client("iam"), D7_POLICY)
        if self._bucket:
            cleanup_bucket(self._aws.sandbox.client("s3"), self._bucket)


class D8FailAuditClose:
    """Deny close.json writes after a successful create; outcome must be UNKNOWN."""

    def __init__(self) -> None:
        self._aws = connect_live()
        self._suffix = f"d8{uuid.uuid4().hex[:12]}"
        self._bucket = f"{SANDBOX_BUCKET_PREFIX}{self._suffix}"
        self._request = requests.create_bucket_request(
            suffix=self._suffix, purpose="phase5-d8", idempotency_key=self._suffix
        )
        self._cid = canonical_request_id(self._request)
        self._close_arn = (
            f"arn:aws:s3:::{self._aws.outputs['audit_bucket']}/audit/{self._cid}/close.json"
        )
        self._canonical_id = self._cid

    def break_it(self) -> None:
        _delete_role_policy(self._aws.core.client("iam"), D8_POLICY)
        _deny_audit_put(self._aws, [self._close_arn], "Phase5D8DenyAuditClose")
        time.sleep(1)

    def assert_correct_failure(self) -> None:
        result = _broker(self._aws, self._request.as_json())
        assert result["outcome"] == "UNKNOWN", result
        self._aws.sandbox.client("s3").head_bucket(Bucket=self._bucket)
        claim = (
            self._aws.core.resource("dynamodb")
            .Table("rootstock-claims")
            .get_item(Key={"canonical_id": self._canonical_id}, ConsistentRead=True)
            .get("Item")
        )
        assert claim is not None, "claim missing after AUDIT CLOSE failure"
        assert str(claim["state"]) == "UNKNOWN", claim
        assert bool(claim.get("incident")) is True, claim

    def restore(self) -> None:
        _clear_audit_bucket_policy(self._aws)
        _delete_role_policy(self._aws.core.client("iam"), D8_POLICY)

    def assert_reconciled(self) -> None:
        result: dict[str, Any] | None = None
        for _ in range(20):
            result = _broker(self._aws, self._request.as_json())
            if result["outcome"] == "SUCCESS" and result.get("rule") == "reconcile.provider":
                break
            if result["outcome"] == "UNKNOWN":
                time.sleep(3)
                continue
            break
        assert result is not None
        assert result["outcome"] == "SUCCESS", result
        assert result["rule"] == "reconcile.provider", result
        claim = (
            self._aws.core.resource("dynamodb")
            .Table("rootstock-claims")
            .get_item(Key={"canonical_id": self._canonical_id}, ConsistentRead=True)
            .get("Item")
        )
        assert claim is not None
        assert str(claim["state"]) == "EXECUTED", claim

    def cleanup(self) -> None:
        cleanup_bucket(self._aws.sandbox.client("s3"), self._bucket)


def d1() -> DestructiveTest:
    return D1KillRuntime()


def d2() -> DestructiveTest:
    return D2AlterConstitution()


def d3() -> DestructiveTest:
    return D3RuntimeCannotAssume()


def d4() -> DestructiveTest:
    return D4Replay()


def d5() -> DestructiveTest:
    return D5Undeclared()


def d6() -> DestructiveTest:
    return D6OutOfScope()


def d7() -> DestructiveTest:
    return D7RevokeAuditOpen()


def d8() -> DestructiveTest:
    return D8FailAuditClose()
