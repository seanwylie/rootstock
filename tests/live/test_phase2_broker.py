"""Phase 2 live checks through the broker Lambda (no SSO assume of broker-role)."""

from __future__ import annotations

import time
from typing import Any

import pytest

from rootstock.shared.capability import Outcome
from rootstock.shared.vocabulary import SANDBOX_BUCKET_PREFIX
from tests.fixtures import requests
from tests.live.helpers import invoke_lambda, tf_outputs

pytestmark = pytest.mark.live


def _sandbox_s3() -> Any:
    import boto3

    return boto3.Session(profile_name="rootstock-sandbox", region_name="us-east-1").client("s3")


def test_live_create_replay_via_lambda() -> None:
    import uuid

    import boto3
    from check_aws_context import check_identity, load_accounts, resolve_profile

    accounts = load_accounts()
    check_identity(accounts, resolve_profile(accounts, "rootstock-core"), expect_zone="core")
    check_identity(accounts, resolve_profile(accounts, "rootstock-sandbox"), expect_zone="sandbox")

    outputs = tf_outputs()
    core = boto3.Session(profile_name="rootstock-core", region_name="us-east-1")
    suffix = f"p2{uuid.uuid4().hex[:12]}"
    bucket = f"{SANDBOX_BUCKET_PREFIX}{suffix}"
    s3 = _sandbox_s3()
    request = requests.create_bucket_request(suffix=suffix, purpose="phase2-live")
    try:
        first = invoke_lambda(core, outputs["broker_function_name"], request.as_json())
        assert first["outcome"] == Outcome.SUCCESS, first
        s3.head_bucket(Bucket=bucket)
        tagging = s3.get_bucket_tagging(Bucket=bucket)
        tags = {t["Key"]: t["Value"] for t in tagging["TagSet"]}
        assert tags["rootstock:managed-by"] == "rootstock"
        assert tags["rootstock:purpose"] == "phase2-live"

        second = invoke_lambda(core, outputs["broker_function_name"], request.as_json())
        assert second["outcome"] == Outcome.DUPLICATE
        assert second["audit_id"] == first["audit_id"]

        undeclared = invoke_lambda(
            core,
            outputs["broker_function_name"],
            requests.undeclared_capability_request(idempotency_key=suffix).as_json(),
        )
        assert undeclared["outcome"] == Outcome.REJECTED
        assert undeclared["rule"] == "schema.undeclared_capability"

        denied = invoke_lambda(
            core,
            outputs["broker_function_name"],
            requests.out_of_scope_request(idempotency_key=f"{suffix}-oos").as_json(),
        )
        assert denied["outcome"] == Outcome.DENIED
        assert denied["rule"] == "scope.target"
    finally:
        _cleanup_bucket(s3, bucket)


def _cleanup_bucket(s3: Any, bucket: str) -> None:
    from contextlib import suppress

    from botocore.exceptions import ClientError

    with suppress(ClientError):
        s3.delete_bucket(Bucket=bucket)
        return
    time.sleep(1)
    with suppress(ClientError):
        s3.delete_bucket(Bucket=bucket)
