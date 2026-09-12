"""AWS adapters for the runtime Lambda. No sts:AssumeRole anywhere in this module."""

from __future__ import annotations

import json
import os
import secrets
from typing import Any

from rootstock.broker.aws import S3GrantStore
from rootstock.broker.stores import SystemClock
from rootstock.runtime.heartbeat import heartbeat_from_env
from rootstock.runtime.liveness import liveness_from_env
from rootstock.runtime.loop import CycleRunner, DigestConstitution, stub_from_mode
from rootstock.runtime.reasoner import Reasoner
from rootstock.runtime.stores import Cursor, DecisionRecord
from rootstock.shared.claims import ApprovalState, ClaimState


def aws_cycle_runner(*, stub_mode: str = "") -> CycleRunner:
    import boto3

    region = os.environ.get("AWS_REGION", "us-east-1")
    session = boto3.Session(region_name=region)
    grant_bucket = os.environ["GRANT_BUCKET"]
    grants = S3GrantStore(session, grant_bucket)
    expected = os.environ["CONSTITUTION_SHA256"]
    body = (
        session.client("s3").get_object(Bucket=grant_bucket, Key="constitution.json")["Body"].read()
    )
    mode = stub_mode or os.environ.get("STUB_MODE", "normal")
    return CycleRunner(
        constitution=DigestConstitution(grants, expected_digest=expected, body=body),
        grants=grants,
        decisions=DynamoDecisionStore(
            session, os.environ.get("DECISIONS_TABLE", "rootstock-decisions")
        ),
        cursor=DynamoCursorStore(session, os.environ.get("MEMORY_TABLE", "rootstock-memory")),
        memory=DynamoMemoryLog(session, os.environ.get("MEMORY_TABLE", "rootstock-memory")),
        claims=DynamoClaimReader(session, os.environ.get("CLAIMS_TABLE", "rootstock-claims")),
        approvals=DynamoApprovalReader(
            session, os.environ.get("APPROVALS_TABLE", "rootstock-approvals")
        ),
        enqueue=SqsEnqueue(session, os.environ["QUEUE_URL"]),
        reasoner=reasoner_from_env(session, stub_mode=mode),
        clock=SystemClock(),
        heartbeat=heartbeat_from_env(),
        liveness=liveness_from_env(session),
    )


def reasoner_from_env(session: Any, *, stub_mode: str) -> Reasoner:
    """Configuration switch. Default remains the stub until REASONER=model."""
    kind = os.environ.get("REASONER", "stub").strip().lower()
    if kind != "model":
        return stub_from_mode(stub_mode)
    from rootstock.runtime.model import (
        DEFAULT_BEDROCK_MODEL_ID,
        BedrockModelClient,
        ModelReasoner,
        SpendCap,
        load_prompt,
    )

    prompt_key = os.environ.get("PROMPT_KEY", "prompts/v0.json")
    body = (
        session.client("s3")
        .get_object(Bucket=os.environ["GRANT_BUCKET"], Key=prompt_key)["Body"]
        .read()
    )
    prompt = load_prompt(json.loads(body))
    cap_usd = float(prompt.get("max_usd_per_call") or 0.05)
    model_id = os.environ.get("BEDROCK_MODEL_ID", DEFAULT_BEDROCK_MODEL_ID).strip()
    client = BedrockModelClient(session, model_id, cap=SpendCap(cap_usd), call_cost_usd=cap_usd)
    return ModelReasoner(client, prompt)


def _table(session: Any, name: str) -> Any:
    return session.resource("dynamodb").Table(name)


class DynamoCursorStore:
    def __init__(self, session: Any, table: str) -> None:
        self._table = _table(session, table)

    def get(self) -> Cursor:
        response = self._table.get_item(Key={"pk": "runtime", "sk": "cursor"})
        item = response.get("Item")
        if not item:
            return Cursor(next_cycle=1)
        return Cursor(next_cycle=int(item["next_cycle"]))

    def save(self, cursor: Cursor) -> None:
        self._table.put_item(
            Item={"pk": "runtime", "sk": "cursor", "next_cycle": cursor.next_cycle}
        )


class DynamoDecisionStore:
    def __init__(self, session: Any, table: str) -> None:
        self._table = _table(session, table)

    def get(self, cycle_number: int) -> DecisionRecord | None:
        response = self._table.get_item(Key={"cycle_number": cycle_number}, ConsistentRead=True)
        item = response.get("Item")
        if not item:
            return None
        return _decision_from_item(item)

    def open(self, record: DecisionRecord) -> None:
        item = _decision_to_item(record)
        self._table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(cycle_number)",
        )

    def list_closed(self, through_cycle: int) -> list[DecisionRecord]:
        out: list[DecisionRecord] = []
        for n in range(1, through_cycle + 1):
            rec = self.get(n)
            if rec is not None and rec.state == "closed":
                out.append(rec)
        return out


class DynamoMemoryLog:
    def __init__(self, session: Any, table: str) -> None:
        self._table = _table(session, table)

    def append(self, cycle_number: int, body: dict[str, Any]) -> None:
        sk = f"claim#{cycle_number:010d}"
        self._table.put_item(
            Item={
                "pk": "memory",
                "sk": sk,
                "cycle_number": cycle_number,
                "body": json.dumps(body, separators=(",", ":")),
            }
        )

    def recent(self, limit: int = 8) -> list[dict[str, Any]]:
        from boto3.dynamodb.conditions import Key

        response = self._table.query(
            KeyConditionExpression=Key("pk").eq("memory") & Key("sk").begins_with("claim#"),
            ScanIndexForward=False,
            Limit=limit,
        )
        items = []
        for item in response.get("Items") or []:
            raw = json.loads(str(item.get("body") or "{}"))
            if isinstance(raw, dict):
                items.append(raw)
        return list(reversed(items))

    def record_wake(
        self, *, at: int, outcome: str, reason: str, cycle_number: int | None = None
    ) -> None:
        body: dict[str, Any] = {"at": at, "outcome": outcome, "reason": reason}
        if cycle_number is not None:
            body["cycle_number"] = cycle_number
        self._table.put_item(
            Item={
                "pk": "wake",
                "sk": f"{at:010d}#{secrets.token_hex(4)}",
                "body": json.dumps(body, separators=(",", ":")),
            }
        )


class DynamoClaimReader:
    def __init__(self, session: Any, table: str) -> None:
        self._table = _table(session, table)

    def get_state(self, canonical_id: str) -> tuple[ClaimState | None, int | None]:
        response = self._table.get_item(Key={"canonical_id": canonical_id}, ConsistentRead=True)
        item = response.get("Item")
        if not item:
            return None, None
        return ClaimState(str(item["state"])), int(item["lease_expires_at"])


class DynamoApprovalReader:
    def __init__(self, session: Any, table: str) -> None:
        self._table = _table(session, table)

    def get_state(self, canonical_id: str) -> ApprovalState | None:
        response = self._table.get_item(Key={"canonical_id": canonical_id}, ConsistentRead=True)
        item = response.get("Item")
        if not item:
            return None
        return ApprovalState(str(item["state"]))


class SqsEnqueue:
    def __init__(self, session: Any, queue_url: str) -> None:
        self._sqs = session.client("sqs")
        self._url = queue_url

    def send(self, body: dict[str, Any]) -> None:
        self._sqs.send_message(
            QueueUrl=self._url, MessageBody=json.dumps(body, separators=(",", ":"))
        )


def _decision_to_item(record: DecisionRecord) -> dict[str, Any]:
    item: dict[str, Any] = {
        "cycle_number": record.cycle_number,
        "state": record.state,
        "opened_by": record.opened_by,
        "opened_at": record.opened_at,
    }
    if record.closed_by:
        item["closed_by"] = record.closed_by
    if record.observed_hash:
        item["observed_hash"] = record.observed_hash
    if record.expected_outcome:
        item["expected_outcome"] = record.expected_outcome
    if record.capability:
        item["capability"] = record.capability
    if record.canonical_id:
        item["canonical_id"] = record.canonical_id
    if record.request_json is not None:
        item["request_json"] = json.dumps(record.request_json, separators=(",", ":"))
    if record.result_json is not None:
        item["result_json"] = json.dumps(record.result_json, separators=(",", ":"))
    if record.actual_outcome:
        item["actual_outcome"] = record.actual_outcome
    if record.reason:
        item["reason"] = record.reason
    if record.decision:
        item["decision"] = record.decision
    if record.rationale:
        item["rationale"] = record.rationale
    if record.alternatives:
        item["alternatives_json"] = json.dumps(list(record.alternatives), separators=(",", ":"))
    return item


def _decision_from_item(item: dict[str, Any]) -> DecisionRecord:
    request = None
    if item.get("request_json"):
        parsed = json.loads(str(item["request_json"]))
        request = parsed if isinstance(parsed, dict) else None
    result = None
    if item.get("result_json"):
        parsed = json.loads(str(item["result_json"]))
        result = parsed if isinstance(parsed, dict) else None
    return DecisionRecord(
        cycle_number=int(item["cycle_number"]),
        state=str(item["state"]),
        opened_by=str(item.get("opened_by") or "runtime"),
        opened_at=int(item.get("opened_at") or 0),
        closed_by=str(item["closed_by"]) if item.get("closed_by") else None,
        observed_hash=str(item["observed_hash"]) if item.get("observed_hash") else None,
        expected_outcome=str(item["expected_outcome"]) if item.get("expected_outcome") else None,
        capability=str(item["capability"]) if item.get("capability") else None,
        canonical_id=str(item["canonical_id"]) if item.get("canonical_id") else None,
        request_json=request,
        result_json=result,
        actual_outcome=str(item["actual_outcome"]) if item.get("actual_outcome") else None,
        reason=str(item["reason"]) if item.get("reason") else None,
        alternatives=_alternatives(item),
        rationale=str(item["rationale"]) if item.get("rationale") else "",
        decision=str(item.get("decision") or ""),
    )


def _alternatives(item: dict[str, Any]) -> tuple[str, ...]:
    raw = item.get("alternatives_json")
    if not raw:
        return ()
    parsed = json.loads(str(raw))
    if not isinstance(parsed, list):
        return ()
    return tuple(str(x) for x in parsed)
