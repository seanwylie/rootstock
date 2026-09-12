#!/usr/bin/env python3
"""Phase 7: observe 100 EventBridge-driven cycles. Does not invoke the runtime."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from check_aws_context import WrongContextError, check_identity, load_accounts, resolve_profile

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs" / "plans" / "v0" / "evidence" / "phase-7-run.json"
COUNT = 100
POLL_SECONDS = 15.0
TIMEOUT_SECONDS = 150 * 60
OPERATOR = "RootstockSandboxOperatorRole"
GB_SECOND_USD = 0.0000166667
REQUEST_USD = 0.0000002


def _cleared_env() -> dict[str, str]:
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
    home_bin = str(Path.home() / ".local" / "bin")
    if home_bin not in env.get("PATH", ""):
        env["PATH"] = f"{home_bin}:{env.get('PATH', '')}"
    return env


def _tf_outputs() -> dict[str, Any]:
    raw = subprocess.check_output(
        ["terraform", f"-chdir={REPO / 'infra' / 'v0'}", "output", "-json"],
        env=_cleared_env(),
    )
    parsed = json.loads(raw)
    return {k: v["value"] for k, v in parsed.items()}


def _cursor(table: Any) -> int:
    item = table.get_item(Key={"pk": "runtime", "sk": "cursor"}).get("Item")
    if not item:
        return 1
    return int(item["next_cycle"])


def _decision(table: Any, cycle: int) -> dict[str, Any] | None:
    item = table.get_item(Key={"cycle_number": cycle}, ConsistentRead=True).get("Item")
    return item if isinstance(item, dict) else None


def _wait_closed(table: Any, first: int, count: int, *, started: float) -> list[dict[str, Any]]:
    last = first + count - 1
    closed: dict[int, dict[str, Any]] = {}
    while time.time() - started < TIMEOUT_SECONDS:
        ready = 0
        for n in range(first, last + 1):
            if n in closed:
                ready += 1
                continue
            item = _decision(table, n)
            if item is None or str(item.get("state")) != "closed":
                continue
            closed[n] = item
            ready += 1
        print(
            f"qualification closed={ready}/{count} next_needed={first + ready} "
            f"elapsed={int(time.time() - started)}s",
            flush=True,
        )
        if ready >= count:
            return [closed[n] for n in range(first, last + 1)]
        time.sleep(POLL_SECONDS)
    raise SystemExit(f"timed out after {TIMEOUT_SECONDS}s with {len(closed)}/{count} closed cycles")


def _memory_body(table: Any, cycle_number: int) -> dict[str, Any] | None:
    item = table.get_item(Key={"pk": "memory", "sk": f"claim#{cycle_number:010d}"}).get("Item")
    if not item:
        return None
    raw = json.loads(str(item.get("body") or "{}"))
    return raw if isinstance(raw, dict) else None


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


def _event_arn(event: dict[str, Any]) -> str:
    identity = event.get("userIdentity") or {}
    if isinstance(identity, dict):
        return str(identity.get("arn") or "")
    return ""


def _session_name(event: dict[str, Any]) -> str:
    arn = _event_arn(event)
    return arn.rsplit("/", 1)[-1] if "/" in arn else arn


def _duration_ms(
    session: Any, function_name: str, start: datetime, end: datetime
) -> tuple[int, int]:
    points = (
        session.client("cloudwatch")
        .get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName="Duration",
            Dimensions=[{"Name": "FunctionName", "Value": function_name}],
            StartTime=start,
            EndTime=end,
            Period=60,
            Statistics=["Average", "SampleCount"],
        )
        .get("Datapoints")
        or []
    )
    samples = sum(float(p.get("SampleCount") or 0) for p in points)
    if samples <= 0:
        return 0, 0
    total = sum(float(p["Average"]) * float(p["SampleCount"]) for p in points)
    return max(1, int(total / samples)), int(samples)


def _lambda_usd(duration_ms: int, memory_mb: int = 256) -> float:
    gb_seconds = (memory_mb / 1024) * (duration_ms / 1000)
    return gb_seconds * GB_SECOND_USD + REQUEST_USD


def main() -> int:
    try:
        accounts = load_accounts()
        check_identity(accounts, resolve_profile(accounts, "rootstock-core"), expect_zone="core")
        check_identity(
            accounts, resolve_profile(accounts, "rootstock-sandbox"), expect_zone="sandbox"
        )
    except WrongContextError as exc:
        print(f"\nAWS context check FAILED\n\n{exc}\n", file=sys.stderr)
        return 2

    import boto3

    outputs = _tf_outputs()
    if str(outputs.get("wake_rule_state")) != "ENABLED":
        print("wake rule is not ENABLED", file=sys.stderr)
        return 1
    core = boto3.Session(profile_name="rootstock-core", region_name="us-east-1")
    sandbox = boto3.Session(profile_name="rootstock-sandbox", region_name="us-east-1")
    lam = core.client("lambda")
    env = lam.get_function_configuration(FunctionName=str(outputs["runtime_function_name"]))[
        "Environment"
    ]["Variables"]
    if env.get("REASONER", "stub") != "stub":
        print("REASONER is not stub; refusing to qualify inference", file=sys.stderr)
        return 1

    decisions = core.resource("dynamodb").Table("rootstock-decisions")
    memory = core.resource("dynamodb").Table("rootstock-memory")
    claims = core.resource("dynamodb").Table("rootstock-claims")
    first = _cursor(memory)
    window_start = datetime.now(UTC) - timedelta(seconds=30)
    print(f"watching for {COUNT} closed cycles starting at {first}", flush=True)
    started = time.time()
    rows = _wait_closed(decisions, first, COUNT, started=started)
    last_n = int(rows[-1]["cycle_number"])

    for row in rows:
        cycle = row.get("cycle_number")
        if str(row.get("opened_by")) != "runtime":
            print(f"cycle {cycle} opened_by={row.get('opened_by')}", file=sys.stderr)
            return 1
        if str(row.get("state")) != "closed":
            print(f"cycle {cycle} state={row.get('state')}", file=sys.stderr)
            return 1
        if str(row.get("closed_by")) != "broker":
            print(f"cycle {cycle} closed_by={row.get('closed_by')}", file=sys.stderr)
            return 1

    mid = rows[COUNT // 2]
    prior_n = int(mid["cycle_number"]) - 1
    learned = _memory_body(memory, prior_n)
    if not learned or ("claim" not in learned and learned.get("kind") != "learned"):
        print(f"memory missing learned claim for cycle {prior_n}: {learned}", file=sys.stderr)
        return 1
    later = _decision(decisions, int(mid["cycle_number"]) + 1)
    if later is None or not later.get("observed_hash"):
        print(
            "later cycle did not persist observed_hash (OBSERVE reads memory.recent())",
            file=sys.stderr,
        )
        return 1

    print("waiting for CloudTrail ingest...", flush=True)
    time.sleep(90)
    orphans: list[str] = []
    joined = 0
    events = _lookup_create_buckets(sandbox, window_start, datetime.now(UTC) + timedelta(minutes=2))
    for event in events:
        if OPERATOR not in _event_arn(event):
            continue
        name = _session_name(event)
        if name.startswith("reconcile"):
            continue
        claim_row = claims.get_item(Key={"canonical_id": name}).get("Item")
        if claim_row is None:
            orphans.append(name)
        else:
            joined += 1
    if orphans:
        print(f"CloudTrail CreateBucket session names with no claim: {orphans}", file=sys.stderr)
        return 1

    window_end = datetime.now(UTC) + timedelta(minutes=1)
    runtime_ms, runtime_n = _duration_ms(
        core, str(outputs["runtime_function_name"]), window_start, window_end
    )
    broker_ms, broker_n = _duration_ms(
        core, str(outputs["broker_function_name"]), window_start, window_end
    )
    cost_usd = _lambda_usd(runtime_ms or 1) + _lambda_usd(broker_ms or 1)

    report = {
        "count": COUNT,
        "first_cycle": first,
        "last_cycle": last_n,
        "elapsed_seconds": int(time.time() - started),
        "wake_state": outputs.get("wake_rule_state"),
        "wake_schedule": outputs.get("wake_schedule"),
        "reasoner": env.get("REASONER", "stub"),
        "memory_prior_cycle": prior_n,
        "memory_kind": learned.get("kind") or "claim",
        "memory_expected_outcome_met": (
            learned.get("expected_outcome_met")
            if "expected_outcome_met" in learned
            else (learned.get("evidence") or {}).get("expected_outcome_met")
        ),
        "later_cycle_observed_hash": later.get("observed_hash"),
        "cloudtrail_joined": joined,
        "cloudtrail_orphans": orphans,
        "runtime_ms": runtime_ms,
        "runtime_samples": runtime_n,
        "broker_ms": broker_ms,
        "broker_samples": broker_n,
        "cost_usd": cost_usd,
        "finished_at": datetime.now(UTC).isoformat(),
    }
    EVIDENCE.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)
    print(f"wrote {EVIDENCE}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
