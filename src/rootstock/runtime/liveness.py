"""Signals the runtime can emit without reaching Sandbox: expired-lease, etc."""

from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger("rootstock.runtime.liveness")

NAMESPACE = "Rootstock"


class LivenessSink(Protocol):
    def expired_lease(self, cycle: int) -> None: ...


class NoopLiveness:
    def expired_lease(self, cycle: int) -> None:
        del cycle
        return


class RecordingLiveness:
    def __init__(self) -> None:
        self.expired: list[int] = []

    def expired_lease(self, cycle: int) -> None:
        self.expired.append(cycle)


class CloudWatchLiveness:
    def __init__(self, session: object, *, namespace: str = NAMESPACE) -> None:
        self._cw = session.client("cloudwatch")  # type: ignore[attr-defined]
        self._namespace = namespace

    def expired_lease(self, cycle: int) -> None:
        self._cw.put_metric_data(
            Namespace=self._namespace,
            MetricData=[
                {
                    "MetricName": "ExpiredLease",
                    "Value": 1,
                    "Unit": "Count",
                    "Dimensions": [{"Name": "cycle", "Value": str(cycle)}],
                }
            ],
        )


def liveness_from_env(session: object | None = None) -> LivenessSink:
    if session is None:
        return NoopLiveness()
    return CloudWatchLiveness(session)
