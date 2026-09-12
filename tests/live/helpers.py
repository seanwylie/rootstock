"""Shared helpers for live AWS tests."""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]


def cleared_env() -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in {
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
            "AWS_DEFAULT_PROFILE",
        }
    }
    env["AWS_PROFILE"] = "rootstock-core"
    env["PATH"] = os.environ.get("PATH", "")
    home_bin = str(Path.home() / ".local" / "bin")
    if home_bin not in env["PATH"]:
        env["PATH"] = f"{home_bin}:{env['PATH']}"
    return env


def tf_outputs() -> dict[str, Any]:
    raw = subprocess.check_output(
        ["terraform", f"-chdir={REPO / 'infra' / 'v0'}", "output", "-json"],
        env=cleared_env(),
    )
    parsed = json.loads(raw)
    return {k: v["value"] for k, v in parsed.items()}


def invoke_lambda(session: Any, name: str, payload: dict[str, Any]) -> dict[str, Any]:
    client = session.client("lambda")
    response = client.invoke(
        FunctionName=name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )
    body = json.loads(response["Payload"].read())
    if response.get("FunctionError"):
        raise AssertionError(body)
    if not isinstance(body, dict):
        raise AssertionError(f"lambda returned {body!r}")
    return body


@dataclass
class LiveAws:
    outputs: dict[str, Any]
    core: Any
    sandbox: Any


def connect_live() -> LiveAws:
    import boto3
    from check_aws_context import check_identity, load_accounts, resolve_profile

    accounts = load_accounts()
    check_identity(accounts, resolve_profile(accounts, "rootstock-core"), expect_zone="core")
    check_identity(accounts, resolve_profile(accounts, "rootstock-sandbox"), expect_zone="sandbox")
    return LiveAws(
        outputs=tf_outputs(),
        core=boto3.Session(profile_name="rootstock-core", region_name="us-east-1"),
        sandbox=boto3.Session(profile_name="rootstock-sandbox", region_name="us-east-1"),
    )


def cleanup_bucket(s3: Any, bucket: str) -> None:
    from contextlib import suppress

    from botocore.exceptions import ClientError

    with suppress(ClientError):
        s3.delete_bucket(Bucket=bucket)
        return
    time.sleep(1)
    with suppress(ClientError):
        s3.delete_bucket(Bucket=bucket)


def simulate(session: Any, role_arn: str, action: str, resource: str) -> str:
    result = session.client("iam").simulate_principal_policy(
        PolicySourceArn=role_arn,
        ActionNames=[action],
        ResourceArns=[resource],
    )["EvaluationResults"]
    if not result:
        return "implicitDeny"
    return str(result[0]["EvalDecision"])


def wait_until_denied(
    session: Any,
    role_arn: str,
    action: str,
    resource: str,
    *,
    timeout: float = 45.0,
) -> None:
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        last = simulate(session, role_arn, action, resource)
        if last.lower() != "allowed":
            return
        time.sleep(2)
    raise AssertionError(f"{action} on {resource} still allowed after {timeout}s ({last})")


def wait_until_allowed(
    session: Any,
    role_arn: str,
    action: str,
    resource: str,
    *,
    timeout: float = 45.0,
) -> None:
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        last = simulate(session, role_arn, action, resource)
        if last.lower() == "allowed":
            return
        time.sleep(2)
    raise AssertionError(f"{action} on {resource} still {last} after {timeout}s")
