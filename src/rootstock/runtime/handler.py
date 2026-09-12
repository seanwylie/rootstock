"""Lambda handler: one wake, then dormant."""

from __future__ import annotations

import json
from typing import Any

from rootstock.runtime.loop import CycleResult, CycleRunner


def handler(event: dict[str, Any] | None, context: object) -> dict[str, Any]:
    del context
    payload = event or {}
    runner = runner_from_env(stub_mode=str(payload.get("stub_mode") or ""))
    result = runner.run()
    return result.as_json()


def runner_from_env(*, stub_mode: str = "") -> CycleRunner:
    from rootstock.runtime.aws import aws_cycle_runner

    return aws_cycle_runner(stub_mode=stub_mode)


def result_json(result: CycleResult) -> str:
    return json.dumps(result.as_json(), separators=(",", ":"))
