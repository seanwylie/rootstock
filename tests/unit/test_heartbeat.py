"""Phase 4: heartbeat.ping() is the only outbound HTTP; silence alerts."""

from __future__ import annotations

import inspect
from pathlib import Path
from urllib.error import URLError

import pytest

from rootstock.broker.stores import LEASE_SECONDS, ClaimRecord, FrozenClock
from rootstock.runtime.heartbeat import DeadMansSwitch, HttpHeartbeat
from rootstock.runtime.loop import in_memory_runtime
from rootstock.runtime.reasoner import StubMode, StubReasoner
from rootstock.shared.claims import ClaimState

SRC = Path(__file__).resolve().parents[2] / "src"


def test_ping_takes_no_arguments() -> None:
    assert list(inspect.signature(HttpHeartbeat.ping).parameters) == ["self"]


def test_http_heartbeat_rejects_non_https() -> None:
    with pytest.raises(ValueError, match="https"):
        HttpHeartbeat("http://example.invalid/ping")


def test_http_heartbeat_get_is_the_only_call_site(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    class _Resp:
        def read(self) -> bytes:
            return b""

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def fake_urlopen(url: str, timeout: float = 0) -> _Resp:
        seen.append(url)
        del timeout
        return _Resp()

    monkeypatch.setattr("rootstock.runtime.heartbeat.urllib.request.urlopen", fake_urlopen)
    HttpHeartbeat("https://hc-ping.example/abc").ping()
    assert seen == ["https://hc-ping.example/abc"]


def test_every_cycle_outcome_pings() -> None:
    clock = FrozenClock(1_000_000)
    _, harness = in_memory_runtime(clock=clock)
    assert harness.wake().action == "enqueued"
    skipped = harness.wake()
    assert skipped.action == "skipped"
    clock.t = 1_000_000 + LEASE_SECONDS + 1
    halted = harness.wake()
    assert halted.action == "halted"
    _, noop_harness = in_memory_runtime(reasoner=StubReasoner(StubMode.NOOP))
    assert noop_harness.wake().action == "noop"
    assert len(harness.heartbeat.pings) == 3
    assert len(noop_harness.heartbeat.pings) == 1


def test_expired_lease_emits_liveness_signal() -> None:
    clock = FrozenClock(1_000_000)
    _, harness = in_memory_runtime(clock=clock)
    first = harness.wake()
    record = harness.decisions.get(first.cycle_number)
    assert record is not None and record.canonical_id
    harness.claims.save(
        ClaimRecord(
            canonical_id=record.canonical_id,
            state=ClaimState.PENDING,
            lease_expires_at=1_000_000 - 1,
            attempt=1,
        )
    )
    halted = harness.wake()
    assert halted.action == "halted"
    assert harness.liveness.expired == [halted.cycle_number]


def test_silence_after_window_alerts() -> None:
    clock = FrozenClock(10.0)
    switch = DeadMansSwitch(window_seconds=5, clock=clock)
    switch.ping()
    clock.t = 14.0
    assert switch.observe() is False
    clock.t = 16.0
    assert switch.observe() is True
    assert switch.alerted is True


def test_no_http_request_helper_and_exactly_one_urlopen() -> None:
    helpers: list[Path] = []
    urlopen_files: list[Path] = []
    for path in SRC.rglob("*.py"):
        text = path.read_text()
        for line in text.splitlines():
            stripped = line.split("#", 1)[0]
            if "def http_request" in stripped or "def send_http_request" in stripped:
                helpers.append(path)
            if "urlopen(" in stripped:
                urlopen_files.append(path)
    assert helpers == []
    assert urlopen_files == [SRC / "rootstock" / "runtime" / "heartbeat.py"]


def test_urlopen_failure_does_not_block_the_cycle(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(url: str, timeout: float = 0) -> object:
        del url, timeout
        raise URLError("monitor down")

    monkeypatch.setattr("rootstock.runtime.heartbeat.urllib.request.urlopen", boom)
    from rootstock.runtime.heartbeat import HttpHeartbeat
    from rootstock.runtime.loop import filesystem_constitution, in_memory_runtime

    constitution = filesystem_constitution()
    _, harness = in_memory_runtime(constitution=constitution)
    harness.runtime.heartbeat = HttpHeartbeat("https://hc-ping.example/x")
    result = harness.wake()
    assert result.action == "enqueued"
