#!/usr/bin/env python3
"""Phase 7b: supervised Terra cycles. Invokes the runtime. Never enables EventBridge.

Cost rule: wake must stay DISABLED. REASONER=model is a temporary Lambda env flip
restored in `finally`. If this process dies, `make v0-apply` restores stub from
terraform defaults. Combining ENABLED wake with model is refused here and in
terraform.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from botocore.config import Config
from check_aws_context import check_identity, load_accounts, resolve_profile

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs" / "plans" / "v0" / "evidence" / "phase-7b-run.json"
COUNT = 12
CLOSE_TIMEOUT = 90.0
# Geo CRIS (us.openai.gpt-5.6-terra) in-region-equivalent Bedrock list, Aug 2026.
TERRA_INPUT_USD = 2.20 / 1_000_000
TERRA_OUTPUT_USD = 13.20 / 1_000_000
GB_SECOND_USD = 0.0000166667
REQUEST_USD = 0.0000002
STUB_QUALIFIED_THROUGH = 172


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


def refuse_if_wake_enabled(wake_state: str) -> None:
    if str(wake_state) != "DISABLED":
        raise SystemExit(
            f"refusing: wake is {wake_state}. 7b is supervised invokes only. "
            "Disable EventBridge before any REASONER=model flip. "
            "This is the control that stops unattended Terra spend."
        )


def _lambda_usd(duration_ms: float, *, memory_mb: int = 256) -> float:
    gb_seconds = (memory_mb / 1024.0) * (duration_ms / 1000.0)
    return gb_seconds * GB_SECOND_USD + REQUEST_USD


def _cursor(table: Any) -> int:
    item = table.get_item(Key={"pk": "runtime", "sk": "cursor"}).get("Item")
    if not item:
        return 1
    return int(item["next_cycle"])


def _env_of(lam: Any, name: str) -> dict[str, str]:
    cfg = lam.get_function_configuration(FunctionName=name)
    raw = (cfg.get("Environment") or {}).get("Variables") or {}
    return {str(k): str(v) for k, v in raw.items()}


def _wait_updated(lam: Any, name: str) -> None:
    deadline = time.time() + 60
    while time.time() < deadline:
        cfg = lam.get_function_configuration(FunctionName=name)
        status = str(cfg.get("LastUpdateStatus") or "")
        if status == "Successful":
            return
        if status == "Failed":
            raise RuntimeError(f"lambda update failed: {cfg.get('LastUpdateStatusReason')}")
        time.sleep(2)
    raise TimeoutError(f"lambda {name} update did not finish")


def _set_reasoner(lam: Any, name: str, value: str) -> str:
    env = _env_of(lam, name)
    previous = env.get("REASONER", "stub")
    env["REASONER"] = value
    lam.update_function_configuration(FunctionName=name, Environment={"Variables": env})
    _wait_updated(lam, name)
    return previous


def _invoke(lam: Any, name: str) -> dict[str, Any]:
    response = lam.invoke(
        FunctionName=name,
        InvocationType="RequestResponse",
        Payload=b"{}",
    )
    body = json.loads(response["Payload"].read())
    if response.get("FunctionError"):
        raise RuntimeError(body)
    if not isinstance(body, dict):
        raise RuntimeError(f"lambda returned {body!r}")
    return body


def _wait_closed(decisions: Any, cycle: int) -> dict[str, Any]:
    deadline = time.time() + CLOSE_TIMEOUT
    while time.time() < deadline:
        item = decisions.get_item(Key={"cycle_number": cycle}, ConsistentRead=True).get("Item")
        if isinstance(item, dict) and str(item.get("state")) == "closed":
            return item
        time.sleep(2)
    raise TimeoutError(f"cycle {cycle} did not close in {CLOSE_TIMEOUT}s")


def _sandbox_cycle_buckets(s3: Any) -> list[int]:
    numbers: list[int] = []
    for bucket in s3.list_buckets().get("Buckets") or ():
        name = str(bucket.get("Name") or "")
        prefix = "rootstock-sbx-cycle-"
        if not name.startswith(prefix):
            continue
        suffix = name.removeprefix(prefix)
        if suffix.isdigit():
            numbers.append(int(suffix))
    return sorted(numbers)


def main() -> int:
    import boto3

    accounts = load_accounts()
    check_identity(accounts, resolve_profile(accounts, "rootstock-core"), expect_zone="core")
    check_identity(accounts, resolve_profile(accounts, "rootstock-sandbox"), expect_zone="sandbox")

    outputs = _tf_outputs()
    refuse_if_wake_enabled(str(outputs.get("wake_rule_state")))

    core = boto3.Session(profile_name="rootstock-core", region_name="us-east-1")
    sandbox = boto3.Session(profile_name="rootstock-sandbox", region_name="us-east-1")
    lam = core.client("lambda", config=Config(read_timeout=130, retries={"max_attempts": 0}))
    events = core.client("events")
    runtime_name = str(outputs["runtime_function_name"])
    decisions = core.resource("dynamodb").Table("rootstock-decisions")
    memory = core.resource("dynamodb").Table("rootstock-memory")

    live_wake = events.describe_rule(Name="rootstock-runtime-wake")
    refuse_if_wake_enabled(str(live_wake.get("State")))

    env = _env_of(lam, runtime_name)
    if env.get("REASONER", "stub") == "model":
        print("REASONER was already model; 7b will still restore stub", file=sys.stderr)

    leftover = _sandbox_cycle_buckets(sandbox.client("s3"))
    extras = [n for n in leftover if n > STUB_QUALIFIED_THROUGH]
    print(
        f"sandbox cycle buckets={len(leftover)} extras_after_{STUB_QUALIFIED_THROUGH}={extras}",
        flush=True,
    )

    first_cycle = _cursor(core.resource("dynamodb").Table("rootstock-memory"))
    started = time.time()
    window_start = datetime.now(UTC)
    results: list[dict[str, Any]] = []
    flipped = False
    restore_ok = False
    error: str | None = None
    try:
        print("setting REASONER=model (wake stays DISABLED)", flush=True)
        _set_reasoner(lam, runtime_name, "model")
        flipped = True
        refuse_if_wake_enabled(
            str(events.describe_rule(Name="rootstock-runtime-wake").get("State"))
        )

        while len([r for r in results if r.get("action") in {"noop", "enqueued"}]) < COUNT:
            refuse_if_wake_enabled(
                str(events.describe_rule(Name="rootstock-runtime-wake").get("State"))
            )
            body = _invoke(lam, runtime_name)
            action = str(body.get("action") or "")
            cycle = int(body.get("cycle_number") or 0)
            row: dict[str, Any] = {
                "cycle_number": cycle,
                "action": action,
                "reason": body.get("reason"),
                "input_tokens": body.get("input_tokens"),
                "output_tokens": body.get("output_tokens"),
                "canonical_id": body.get("canonical_id"),
                "expected_outcome_met": body.get("expected_outcome_met"),
            }
            if action == "skipped":
                print(f"wake skipped (not a cycle): {row}", flush=True)
                time.sleep(3)
                continue
            if action == "halted":
                error = "halted"
                results.append(row)
                print(f"HALT {row}", file=sys.stderr)
                break
            if action == "enqueued":
                closed = _wait_closed(decisions, cycle)
                row["state"] = closed.get("state")
                row["capability"] = closed.get("capability")
                row["actual_outcome"] = closed.get("actual_outcome")
                row["closed_by"] = closed.get("closed_by")
                row["expected_outcome"] = closed.get("expected_outcome")
            elif action == "noop":
                rec = decisions.get_item(Key={"cycle_number": cycle}, ConsistentRead=True).get(
                    "Item"
                )
                if rec is not None:
                    row["state"] = rec.get("state")
                    row["actual_outcome"] = rec.get("actual_outcome")
                    row["closed_by"] = rec.get("closed_by")
                    row["expected_outcome"] = rec.get("expected_outcome")
                    row["reason"] = rec.get("reason") or row["reason"]
            else:
                error = f"unexpected action {action}"
                results.append(row)
                break
            results.append(row)
            print(json.dumps(row, default=str), flush=True)
    except Exception as exc:
        error = str(exc)
        print(f"7b failed: {exc}", file=sys.stderr)
    finally:
        print("restoring REASONER=stub", flush=True)
        try:
            _set_reasoner(lam, runtime_name, "stub")
            restore_ok = _env_of(lam, runtime_name).get("REASONER") == "stub"
        except Exception as exc:
            print(f"RESTORE FAILED: {exc}", file=sys.stderr)
        wake_after = str(events.describe_rule(Name="rootstock-runtime-wake").get("State"))
        print(
            f"restore reasoner_stub={restore_ok} wake={wake_after} flipped={flipped}",
            flush=True,
        )
        if wake_after != "DISABLED":
            print("COST ALERT: wake is not DISABLED after 7b", file=sys.stderr)
            restore_ok = False
        if not restore_ok:
            print(
                "make v0-apply restores REASONER=stub and wake=DISABLED from terraform defaults",
                file=sys.stderr,
            )

    cycles = [r for r in results if r.get("action") in {"noop", "enqueued"}]
    input_tokens = sum(int(r.get("input_tokens") or 0) for r in cycles)
    output_tokens = sum(int(r.get("output_tokens") or 0) for r in cycles)
    terra_usd = input_tokens * TERRA_INPUT_USD + output_tokens * TERRA_OUTPUT_USD
    mechanical_usd = 0.000043 * len(cycles)
    learned = None
    memory_prior = None
    if cycles:
        memory_prior = int(cycles[len(cycles) // 2]["cycle_number"]) - 1
        mem = memory.get_item(Key={"pk": "memory", "sk": f"claim#{memory_prior:010d}"}).get("Item")
        if mem is not None:
            learned = json.loads(str(mem.get("body") or "{}"))
    report = {
        "status": "ok" if error is None and restore_ok and len(cycles) == COUNT else "blocked",
        "error": error,
        "count": len(cycles),
        "wanted": COUNT,
        "first_cycle": first_cycle,
        "cycles": cycles,
        "actions": {
            "noop": sum(1 for r in cycles if r.get("action") == "noop"),
            "enqueued": sum(1 for r in cycles if r.get("action") == "enqueued"),
        },
        "elapsed_seconds": int(time.time() - started),
        "window_start": window_start.isoformat(),
        "wake_state": "DISABLED" if restore_ok else "UNKNOWN",
        "reasoner_restored": "stub" if restore_ok else "FAILED",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "terra_usd": terra_usd,
        "mechanical_usd_estimate": mechanical_usd,
        "cycle_usd_estimate": ((terra_usd + mechanical_usd) / len(cycles)) if cycles else None,
        "memory_prior_cycle": memory_prior,
        "memory_claim": learned.get("claim") if isinstance(learned, dict) else None,
        "memory_fields": sorted(learned.keys()) if isinstance(learned, dict) else [],
        "leftover_stub_buckets": len(leftover),
        "extra_stub_cycles_after_172": extras,
        "finished_at": datetime.now(UTC).isoformat(),
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "cycles"}, indent=2), flush=True)
    print(f"wrote {EVIDENCE}", flush=True)
    if not restore_ok:
        return 2
    if error is not None or len(cycles) != COUNT:
        return 1
    print(
        "7b done. wake DISABLED. REASONER=stub. EventBridge was never enabled.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print(
            "interrupted — restore REASONER=stub if the finally block did not run", file=sys.stderr
        )
        raise
