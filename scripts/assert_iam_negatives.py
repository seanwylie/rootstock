#!/usr/bin/env python3
"""Phase 1 exit criteria: prove absence of authority via IAM simulation.

Reads Terraform outputs from infra/v0. Does not trust the .tf source text.
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from check_aws_context import WrongContextError, check_identity, load_accounts, resolve_profile

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_HARNESS = 2


def tf_output() -> dict[str, Any]:
    raw = subprocess.check_output(
        ["terraform", "-chdir=infra/v0", "output", "-json"],
        env=_sandbox_cleared_env(),
    )
    parsed = json.loads(raw)
    return {k: v["value"] for k, v in parsed.items()}


def _sandbox_cleared_env() -> dict[str, str]:
    import os

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
    return env


def simulate(session: Any, role_arn: str, action: str, resource: str) -> str:
    iam = session.client("iam")
    result = iam.simulate_principal_policy(
        PolicySourceArn=role_arn,
        ActionNames=[action],
        ResourceArns=[resource],
    )
    decisions = result["EvaluationResults"]
    if not decisions:
        return "implicitDeny"
    return str(decisions[0]["EvalDecision"])


def must_deny(session: Any, role_arn: str, action: str, resource: str, label: str) -> list[str]:
    decision = simulate(session, role_arn, action, resource)
    if decision.lower() == "allowed":
        return [f"FAIL {label}: {action} on {resource} was allowed"]
    print(f"OK   {label}: {action} → {decision}")
    return []


def main() -> int:
    try:
        accounts = load_accounts()
        profile = resolve_profile(accounts, "rootstock-core")
        check_identity(accounts, profile, expect_zone="core")
    except WrongContextError as exc:
        print(f"\nAWS context check FAILED\n\n{exc}\n", file=sys.stderr)
        return EXIT_HARNESS

    try:
        import boto3
    except ImportError:
        print("boto3 missing", file=sys.stderr)
        return EXIT_HARNESS

    try:
        outputs = tf_output()
    except (subprocess.CalledProcessError, FileNotFoundError, KeyError) as exc:
        print(f"Could not read terraform outputs: {exc}", file=sys.stderr)
        return EXIT_HARNESS

    session = boto3.Session(profile_name="rootstock-core")
    runtime = outputs["runtime_role_arn"]
    broker = outputs["broker_role_arn"]
    account = outputs["core_account_id"]
    grant = f"arn:aws:s3:::{outputs['grant_bucket']}/constitution.json"
    audit = f"arn:aws:s3:::{outputs['audit_bucket']}/probe"
    terra = f"arn:aws:bedrock:us-east-1:{account}:inference-profile/{outputs['bedrock_model_id']}"
    other_model = (
        f"arn:aws:bedrock:us-east-1:{account}:inference-profile/us.anthropic.claude-sonnet-5"
    )
    management_role = "arn:aws:iam::000000000000:role/anything"

    failures: list[str] = []
    failures += must_deny(
        session, runtime, "sts:AssumeRole", management_role, "runtime has no AssumeRole"
    )
    failures += must_deny(
        session,
        runtime,
        "sts:AssumeRole",
        outputs["sandbox_operator_role_arn"],
        "runtime cannot assume sandbox operator",
    )
    failures += must_deny(
        session, runtime, "s3:PutObject", grant, "runtime cannot write grant store"
    )
    failures += must_deny(session, runtime, "s3:DeleteObject", audit, "runtime cannot delete audit")
    failures += must_deny(session, broker, "s3:DeleteObject", audit, "broker cannot delete audit")
    failures += must_deny(
        session,
        broker,
        "bedrock:InvokeModel",
        terra,
        "broker cannot invoke Bedrock",
    )
    failures += must_deny(
        session,
        runtime,
        "bedrock:InvokeModel",
        other_model,
        "runtime cannot invoke models other than Terra",
    )
    failures += must_deny(
        session, broker, "sts:AssumeRole", management_role, "broker cannot assume into Management"
    )

    region = "us-east-1"
    fn = outputs["runtime_function_name"]
    sink = outputs["heartbeat_sink_function_name"]
    runtime_fn = f"arn:aws:lambda:{region}:{account}:function:{fn}"
    sink_fn = f"arn:aws:lambda:{region}:{account}:function:{sink}"
    watch_rule = f"arn:aws:events:{region}:{account}:rule/{outputs['silence_watch_rule_name']}"
    silence_alarm = (
        f"arn:aws:cloudwatch:{region}:{account}:alarm:{outputs['heartbeat_silence_alarm_name']}"
    )
    heartbeat_table = f"arn:aws:dynamodb:{region}:{account}:table/{outputs['heartbeat_table']}"
    silence_param = f"arn:aws:ssm:{region}:{account}:parameter{outputs['heartbeat_silence_param']}"
    failures += must_deny(
        session, runtime, "events:DisableRule", watch_rule, "runtime cannot disable silence watch"
    )
    failures += must_deny(
        session,
        runtime,
        "cloudwatch:DeleteAlarms",
        silence_alarm,
        "runtime cannot delete silence alarm",
    )
    failures += must_deny(
        session,
        runtime,
        "cloudwatch:DisableAlarmActions",
        silence_alarm,
        "runtime cannot silence alarm actions",
    )
    failures += must_deny(
        session,
        runtime,
        "lambda:UpdateFunctionConfiguration",
        runtime_fn,
        "runtime cannot change HEARTBEAT_URL",
    )
    failures += must_deny(
        session, runtime, "lambda:DeleteFunction", sink_fn, "runtime cannot delete heartbeat sink"
    )
    failures += must_deny(
        session, runtime, "dynamodb:PutItem", heartbeat_table, "runtime cannot fake last_ping"
    )
    failures += must_deny(
        session, runtime, "ssm:PutParameter", silence_param, "runtime cannot extend silence window"
    )

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return EXIT_FAIL
    print("All IAM negative assertions passed.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
