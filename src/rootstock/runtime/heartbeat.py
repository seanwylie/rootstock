"""heartbeat.ping() — outbound HTTP with a fixed URL and no arguments.

The URL is constructor configuration. ping() takes no arguments, so a caller cannot
aim it at a different host (AR-16). There is no http_request() helper. This is the
only urlopen call site; inference uses Bedrock over IAM, not HTTP.
"""

from __future__ import annotations

import logging
import os
import urllib.request
from typing import Protocol
from urllib.parse import urlparse

logger = logging.getLogger("rootstock.runtime.heartbeat")

ALLOWED_SCHEME = "https"


class Heartbeat(Protocol):
    def ping(self) -> None:
        """Signal liveness to the configured monitor. No arguments."""


class NoopHeartbeat:
    def ping(self) -> None:
        return


class RecordingHeartbeat:
    """In-process stand-in. Counts pings; never leaves the process."""

    def __init__(self) -> None:
        self.pings: list[float] = []

    def ping(self) -> None:
        import time

        self.pings.append(time.time())


class HttpHeartbeat:
    """GET the configured HTTPS URL. The only urlopen call site."""

    def __init__(self, url: str, *, timeout: float = 5.0) -> None:
        parsed = urlparse(url)
        if parsed.scheme != ALLOWED_SCHEME or not parsed.netloc:
            raise ValueError("heartbeat URL must be https with a host")
        self._url = url
        self._timeout = timeout

    def ping(self) -> None:
        with urllib.request.urlopen(self._url, timeout=self._timeout) as response:
            response.read()


def heartbeat_from_env() -> Heartbeat:
    url = os.environ.get("HEARTBEAT_URL", "").strip()
    if not url:
        return NoopHeartbeat()
    return HttpHeartbeat(url)


class DeadMansSwitch:
    """In-process silence detector. Production uses the watch Lambda + alarm.

    Used to prove the contract: no ping within the window → alert. The live
    monitor is outside this process; this is the unit-test double.
    """

    def __init__(self, *, window_seconds: float, clock: object) -> None:
        self.window_seconds = window_seconds
        self._clock = clock
        self.last_ping_at: float | None = None
        self.alerted = False

    def ping(self) -> None:
        self.last_ping_at = float(self._clock.now())  # type: ignore[attr-defined]
        self.alerted = False

    def observe(self) -> bool:
        now = float(self._clock.now())  # type: ignore[attr-defined]
        if self.last_ping_at is None:
            return False
        if now - self.last_ping_at >= self.window_seconds:
            self.alerted = True
            return True
        return False


def sink_handler(event: dict[str, object] | None, context: object) -> dict[str, object]:
    """Public HTTPS sink. Records last_ping. Runtime cannot write this table itself."""
    del context
    import time

    import boto3

    payload = event or {}
    params = payload.get("queryStringParameters") or {}
    token = ""
    if isinstance(params, dict):
        token = str(params.get("token") or "")
    expected = os.environ.get("HEARTBEAT_TOKEN", "")
    if not expected or token != expected:
        return {"statusCode": 403, "body": ""}
    table = os.environ.get("HEARTBEAT_TABLE", "rootstock-heartbeat")
    boto3.resource("dynamodb").Table(table).put_item(
        Item={"pk": "monitor", "sk": "last", "last_ping": int(time.time())}
    )
    return {"statusCode": 204, "body": ""}
