"""AWS adapters. Used when the broker runs as rootstock-broker-role."""

from __future__ import annotations

import json
import logging
from typing import Any

from rootstock.broker.errors import AuditWriteError, ExecuteError
from rootstock.broker.executor import ExecuteResult, bucket_name
from rootstock.broker.grant_store import (
    CapabilityDeclaration,
    PolicyDocument,
    parse_capability,
    parse_policy,
)
from rootstock.broker.pipeline import Broker
from rootstock.broker.stores import (
    LEASE_SECONDS,
    ApprovalRecord,
    ClaimAttempt,
    ClaimRecord,
)
from rootstock.shared.canonical import canonical_json
from rootstock.shared.capability import CapabilityResult, Cost, Outcome
from rootstock.shared.claims import ApprovalState, ClaimState
from rootstock.shared.vocabulary import DECLARED_AT_V0

logger = logging.getLogger("rootstock.broker")


def _client(session: Any, service: str) -> Any:
    return session.client(service)


class S3GrantStore:
    def __init__(self, session: Any, bucket: str) -> None:
        self._s3 = _client(session, "s3")
        self._bucket = bucket
        self._policy = parse_policy(self._get_json("policy.json"))
        self._caps: dict[str, CapabilityDeclaration] = {}
        for cap_id in DECLARED_AT_V0:
            raw = self._get_json(f"capabilities/{cap_id}.json")
            decl = parse_capability(raw)
            self._caps[decl.id] = decl
        self._session: dict[str, dict[str, Any]] = {}
        create_bucket = "sandbox.s3.create_bucket"
        self._session[create_bucket] = self._get_json(f"session-policies/{create_bucket}.json")

    def _get_json(self, key: str) -> dict[str, Any]:
        obj = self._s3.get_object(Bucket=self._bucket, Key=key)
        raw = json.loads(obj["Body"].read())
        if not isinstance(raw, dict):
            raise ValueError(f"{key} is not a JSON object")
        return raw

    def policy(self) -> PolicyDocument:
        return self._policy

    def capability(self, capability_id: str) -> CapabilityDeclaration | None:
        return self._caps.get(capability_id)

    def declared_ids(self) -> frozenset[str]:
        return frozenset(self._caps) | DECLARED_AT_V0

    def session_policy_template(self, capability_id: str) -> dict[str, Any] | None:
        return self._session.get(capability_id)


class DynamoClaimStore:
    def __init__(self, session: Any, table: str) -> None:
        self._table = session.resource("dynamodb").Table(table)

    def get(self, canonical_id: str) -> ClaimRecord | None:
        response = self._table.get_item(Key={"canonical_id": canonical_id})
        item = response.get("Item")
        if not item:
            return None
        return _claim_from_item(item)

    def try_claim(self, canonical_id: str, now: float) -> ClaimAttempt:
        existing = self.get(canonical_id)
        if existing is None:
            record = ClaimRecord(
                canonical_id=canonical_id,
                state=ClaimState.PENDING,
                lease_expires_at=int(now) + LEASE_SECONDS,
                attempt=1,
            )
            self._table.put_item(
                Item=_claim_to_item(record),
                ConditionExpression="attribute_not_exists(canonical_id)",
            )
            return ClaimAttempt(record=record)
        if existing.state in {ClaimState.EXECUTED, ClaimState.FAILED}:
            return ClaimAttempt(record=existing, duplicate=True)
        if existing.state is ClaimState.UNKNOWN:
            return ClaimAttempt(record=existing, needs_reconcile=True)
        if existing.state is ClaimState.PENDING and existing.lease_expires_at >= int(now):
            return ClaimAttempt(record=existing, duplicate=True)
        existing.attempt += 1
        existing.state = ClaimState.PENDING
        existing.lease_expires_at = int(now) + LEASE_SECONDS
        self.save(existing)
        return ClaimAttempt(record=existing)

    def save(self, record: ClaimRecord) -> None:
        self._table.put_item(Item=_claim_to_item(record))

    def delete(self, canonical_id: str) -> None:
        self._table.delete_item(Key={"canonical_id": canonical_id})


class DynamoApprovalStore:
    def __init__(self, session: Any, table: str) -> None:
        self._table = session.resource("dynamodb").Table(table)

    def get(self, canonical_id: str) -> ApprovalRecord | None:
        response = self._table.get_item(Key={"canonical_id": canonical_id})
        item = response.get("Item")
        if not item:
            return None
        return ApprovalRecord(
            canonical_id=str(item["canonical_id"]),
            state=ApprovalState(str(item["state"])),
            request=json.loads(str(item["request"])),
            expires_at=int(item["expires_at"]),
        )

    def put(self, record: ApprovalRecord) -> None:
        self._table.put_item(
            Item={
                "canonical_id": record.canonical_id,
                "state": record.state.value,
                "request": json.dumps(record.request, separators=(",", ":")),
                "expires_at": record.expires_at,
            }
        )


class S3Audit:
    def __init__(self, session: Any, bucket: str) -> None:
        self._s3 = _client(session, "s3")
        self._bucket = bucket

    def open_record(self, canonical_id: str, body: dict[str, Any]) -> str:
        return self._put(f"audit/{canonical_id}/open.json", body)

    def close_record(self, canonical_id: str, body: dict[str, Any]) -> None:
        self._put(f"audit/{canonical_id}/close.json", body)

    def _put(self, key: str, body: dict[str, Any]) -> str:
        try:
            response = self._s3.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=canonical_json(body),
                ContentType="application/json",
            )
        except Exception as exc:
            raise AuditWriteError(str(exc)) from exc
        version = response.get("VersionId")
        return str(version or key)


class StsSandboxExecutor:
    def __init__(
        self,
        session: Any,
        *,
        role_arn: str,
        external_id: str,
        region: str = "us-east-1",
    ) -> None:
        self._sts = _client(session, "sts")
        self._role_arn = role_arn
        self._external_id = external_id
        self._region = region
        self._last_policy: dict[str, Any] | None = None

    def last_session_policy(self) -> dict[str, Any] | None:
        return self._last_policy

    def create_bucket(
        self,
        *,
        suffix: str,
        purpose: str,
        canonical_id: str,
        session_policy: dict[str, Any],
    ) -> ExecuteResult:
        self._last_policy = session_policy
        name = bucket_name(suffix)
        s3 = self._assumed_s3(canonical_id, session_policy)
        tags = {
            "rootstock:managed-by": "rootstock",
            "rootstock:purpose": purpose,
            "rootstock:environment": "v0",
            "rootstock:owner": "rootstock",
        }
        try:
            s3.create_bucket(Bucket=name)
            s3.put_bucket_tagging(
                Bucket=name,
                Tagging={"TagSet": [{"Key": key, "Value": value} for key, value in tags.items()]},
            )
        except Exception as exc:
            raise ExecuteError(str(exc), side_effect_likely=True) from exc
        return ExecuteResult(bucket=name, tags=tags)

    def bucket_exists(self, bucket: str) -> bool:
        # Reconciliation asks the provider. Use the caller's (broker) credentials via a
        # scoped session without a session policy so HeadBucket is within the role ceiling.
        s3 = self._assumed_s3("reconcile" + "0" * 55, policy=None)
        try:
            s3.head_bucket(Bucket=bucket)
        except Exception as exc:
            name = type(exc).__name__
            code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
            if "404" in str(exc) or code in {"404", "NoSuchBucket", "NotFound"}:
                return False
            if "ClientError" in name and "404" in str(exc):
                return False
            raise
        return True

    def _assumed_s3(self, canonical_id: str, policy: dict[str, Any] | None) -> Any:
        kwargs: dict[str, Any] = {
            "RoleArn": self._role_arn,
            "RoleSessionName": canonical_id[:64],
            "ExternalId": self._external_id,
            "DurationSeconds": 900,
        }
        if policy is not None:
            kwargs["Policy"] = json.dumps(policy, separators=(",", ":"))
        assumed = self._sts.assume_role(**kwargs)
        creds = assumed["Credentials"]
        import boto3

        session = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=self._region,
        )
        return session.client("s3")


class LogIncidents:
    def raise_incident(self, canonical_id: str, reason: str, detail: dict[str, Any]) -> None:
        logger.critical(
            "incident canonical_id=%s reason=%s detail=%s",
            canonical_id,
            reason,
            json.dumps(detail, separators=(",", ":")),
        )


class DynamoDecisionCloser:
    def __init__(self, session: Any, table: str) -> None:
        self._table = session.resource("dynamodb").Table(table)

    def close(self, decision_ref: str | None, result: CapabilityResult) -> None:
        if decision_ref is None:
            return
        try:
            cycle = int(decision_ref)
        except ValueError:
            return
        from botocore.exceptions import ClientError

        try:
            self._table.update_item(
                Key={"cycle_number": cycle},
                UpdateExpression=(
                    "SET #s = :s, result_json = :r, closed_by = :c, actual_outcome = :o"
                ),
                ExpressionAttributeNames={"#s": "state"},
                ExpressionAttributeValues={
                    ":s": "closed",
                    ":r": json.dumps(result.as_json(), separators=(",", ":")),
                    ":c": "broker",
                    ":o": str(result.outcome),
                },
                ConditionExpression="attribute_exists(cycle_number)",
            )
        except ClientError:
            return


def _claim_to_item(record: ClaimRecord) -> dict[str, Any]:
    item: dict[str, Any] = {
        "canonical_id": record.canonical_id,
        "state": record.state.value,
        "lease_expires_at": record.lease_expires_at,
        "attempt": record.attempt,
        "incident": record.incident,
    }
    if record.audit_id:
        item["audit_id"] = record.audit_id
    if record.result is not None:
        item["result_json"] = json.dumps(record.result.as_json(), separators=(",", ":"))
    return item


def _claim_from_item(item: dict[str, Any]) -> ClaimRecord:
    result = None
    if "result_json" in item:
        raw = json.loads(str(item["result_json"]))
        result = CapabilityResult(
            outcome=Outcome(str(raw["outcome"])),
            canonical_id=str(raw["canonical_id"]),
            actual_cost=Cost(**raw.get("actual_cost", {})),
            artifacts=tuple(raw.get("artifacts") or ()),
            audit_id=raw.get("audit_id"),
            error=raw.get("error"),
            rule=raw.get("rule"),
        )
    return ClaimRecord(
        canonical_id=str(item["canonical_id"]),
        state=ClaimState(str(item["state"])),
        lease_expires_at=int(item["lease_expires_at"]),
        attempt=int(item["attempt"]),
        result=result,
        incident=bool(item.get("incident", False)),
        audit_id=str(item["audit_id"]) if item.get("audit_id") else None,
    )


def read_external_id(session: Any, parameter: str = "/rootstock/sandbox-assume-external-id") -> str:
    ssm = _client(session, "ssm")
    response = ssm.get_parameter(Name=parameter, WithDecryption=True)
    return str(response["Parameter"]["Value"])


def live_broker() -> Broker:
    """Broker constructed from Lambda environment. Execution role is rootstock-broker-role."""
    import os

    import boto3

    from rootstock.broker.stores import SystemClock

    session = boto3.Session(region_name=os.environ.get("AWS_REGION", "us-east-1"))
    grant_bucket = os.environ["GRANT_BUCKET"]
    operator = os.environ["SANDBOX_OPERATOR_ROLE_ARN"]
    return Broker(
        grants=S3GrantStore(session, grant_bucket),
        claims=DynamoClaimStore(session, os.environ.get("CLAIMS_TABLE", "rootstock-claims")),
        approvals=DynamoApprovalStore(
            session, os.environ.get("APPROVALS_TABLE", "rootstock-approvals")
        ),
        audit=S3Audit(session, os.environ["AUDIT_BUCKET"]),
        executor=StsSandboxExecutor(
            session,
            role_arn=operator,
            external_id=read_external_id(session),
        ),
        incidents=LogIncidents(),
        decisions=DynamoDecisionCloser(
            session, os.environ.get("DECISIONS_TABLE", "rootstock-decisions")
        ),
        clock=SystemClock(),
    )
