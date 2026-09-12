"""Submit a CapabilityRequest to the broker's ingress without a runtime.

Phase 0 exit criterion 2: submitting to a substrate that does not exist yet must fail with a
clear, actionable error rather than a boto stack trace. A harness whose failure mode is a
wall of traceback trains people to skim failures, which is the opposite of what the
destructive tests need.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

from rootstock.shared.canonical import canonical_json

if TYPE_CHECKING:
    from rootstock.shared.capability import CapabilityRequest

QUEUE_NAME_ENV = "ROOTSTOCK_REQUEST_QUEUE_URL"
REGION_ENV = "AWS_REGION"
DEFAULT_REGION = "us-east-1"


class HarnessError(Exception):
    """Base for harness problems, as distinct from system-under-test failures."""


class SubstrateNotReadyError(HarnessError):
    """The infrastructure this fixture needs has not been built yet.

    Expected during Phase 0 and Phase 1. Distinct from a test failure: nothing is wrong with
    the system under test, because there is not one yet.
    """


class CredentialsUnavailableError(HarnessError):
    """No usable AWS credentials. A local setup problem, not a system failure."""


def _require_boto() -> Any:
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - environment problem, not logic
        raise HarnessError("boto3 is not installed. Run: uv sync --extra dev") from exc
    return boto3


def resolve_queue_url() -> str:
    url = os.environ.get(QUEUE_NAME_ENV)
    if not url:
        raise SubstrateNotReadyError(
            f"{QUEUE_NAME_ENV} is not set, so there is no broker ingress to submit to.\n"
            "This is expected until Phase 1 creates the request queue.\n"
            "Once it exists:\n"
            "  export ROOTSTOCK_REQUEST_QUEUE_URL=$("
            "terraform -chdir=infra/test-env output -raw request_queue_url)"
        )
    return url


def submit(request: CapabilityRequest) -> str:
    """Enqueue a request. Returns the transport message id.

    The transport message id is not the canonical id. The broker derives that itself, from
    request content, precisely so that a caller cannot choose the identity under which its
    request is deduplicated (AR-15).
    """
    boto3 = _require_boto()
    queue_url = resolve_queue_url()
    region = os.environ.get(REGION_ENV, DEFAULT_REGION)

    body = canonical_json(request.as_json()).decode("utf-8")

    try:
        client = boto3.client("sqs", region_name=region)
        response = client.send_message(QueueUrl=queue_url, MessageBody=body)
    except Exception as exc:
        name = type(exc).__name__
        if "NoCredentials" in name or "TokenRetrieval" in name or "SSO" in name:
            raise CredentialsUnavailableError(
                "No usable AWS credentials.\n"
                "Sign in with:  aws sso login\n"
                f"Underlying error: {name}: {exc}"
            ) from exc
        if "NonExistentQueue" in name or "AWS.SimpleQueueService.NonExistentQueue" in str(exc):
            raise SubstrateNotReadyError(
                f"The request queue does not exist at {queue_url}.\n"
                "Expected until Phase 1. Create it with:  make infra-apply"
            ) from exc
        raise

    message_id = response["MessageId"]
    return str(message_id)


def describe(request: CapabilityRequest) -> str:
    """Human-readable rendering, for failure messages."""
    return json.dumps(request.as_json(), indent=2, sort_keys=True)
