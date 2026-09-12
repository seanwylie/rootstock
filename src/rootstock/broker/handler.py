"""Lambda handler: one SQS message, one broker.process."""

from __future__ import annotations

import json
import logging
from typing import Any

from rootstock.broker.pipeline import Broker
from rootstock.broker.schema import request_from_mapping

logger = logging.getLogger("rootstock.broker")


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    del context
    broker = broker_from_env()
    records = event.get("Records")
    if records:
        failures: list[dict[str, str]] = []
        for record in records:
            message_id = str(record.get("messageId") or "")
            try:
                body = record.get("body") or "{}"
                data = json.loads(body) if isinstance(body, str) else body
                if not isinstance(data, dict):
                    raise ValueError("SQS body is not an object")
                request = request_from_mapping(data)
                broker.process(request)
            except Exception:
                logger.exception("broker failed message_id=%s", message_id)
                if message_id:
                    failures.append({"itemIdentifier": message_id})
        return {"batchItemFailures": failures}

    request = request_from_mapping(event)
    result = broker.process(request)
    return result.as_json()


def broker_from_env() -> Broker:
    from rootstock.broker.aws import live_broker

    return live_broker()
