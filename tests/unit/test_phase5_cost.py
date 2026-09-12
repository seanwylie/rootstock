"""Phase 5 cost arithmetic, no AWS."""

from __future__ import annotations

import pytest

from tests.destructive.cost import REQUEST_USD, cycle_cost, lambda_usd


def test_lambda_usd_scales_with_duration_and_memory() -> None:
    short = lambda_usd(duration_ms=1000, memory_mb=256, requests=1)
    long = lambda_usd(duration_ms=2000, memory_mb=256, requests=1)
    fat = lambda_usd(duration_ms=1000, memory_mb=512, requests=1)
    compute_short = short - REQUEST_USD
    assert long == pytest.approx(compute_short * 2 + REQUEST_USD)
    assert fat == pytest.approx(compute_short * 2 + REQUEST_USD)
    assert short > 0


def test_cycle_cost_variance_is_actual_minus_estimate() -> None:
    cost = cycle_cost(runtime_ms=400, broker_ms=800, estimated_usd=0.0)
    assert cost.requests == 2
    assert cost.duration_ms == 1200
    assert cost.actual_usd == cost.variance_usd
    assert 0 < cost.actual_usd < 0.0001
