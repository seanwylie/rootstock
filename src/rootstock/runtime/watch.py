"""Silence watch: not the runtime. Alarms if the heartbeat sink goes quiet."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger("rootstock.runtime.watch")

NAMESPACE = "Rootstock"
DEFAULT_WINDOW = 604800


def handler(event: dict[str, Any] | None, context: object) -> dict[str, Any]:
    del event, context
    import boto3

    table_name = os.environ.get("HEARTBEAT_TABLE", "rootstock-heartbeat")
    window = int(os.environ.get("HEARTBEAT_SILENCE_SECONDS", str(DEFAULT_WINDOW)))
    param = os.environ.get("HEARTBEAT_SILENCE_PARAM", "")
    session = boto3.Session()
    if param:
        got = session.client("ssm").get_parameter(Name=param)
        window = int(got["Parameter"]["Value"])
    item = (
        session.resource("dynamodb")
        .Table(table_name)
        .get_item(Key={"pk": "monitor", "sk": "last"}, ConsistentRead=True)
        .get("Item")
    )
    now = int(time.time())
    if not item or "last_ping" not in item:
        silent = False
        age = None
    else:
        last = int(str(item["last_ping"]))
        age = now - last
        silent = age >= window
    session.client("cloudwatch").put_metric_data(
        Namespace=NAMESPACE,
        MetricData=[
            {
                "MetricName": "HeartbeatSilence",
                "Value": 1 if silent else 0,
                "Unit": "Count",
            }
        ],
    )
    logger.info("silence watch silent=%s age=%s window=%s", silent, age, window)
    return {"silent": silent, "age": age, "window": window}
