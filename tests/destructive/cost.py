"""Cost-per-cycle arithmetic. Prices are us-east-1 x86 Lambda list rates."""

from __future__ import annotations

from dataclasses import dataclass

# AWS Lambda x86 pricing, us-east-1, as of 2026-08. Request fee is $0.20 / 1M.
GB_SECOND_USD = 0.0000166667
REQUEST_USD = 0.0000002
DEFAULT_MEMORY_MB = 256


@dataclass(frozen=True, slots=True)
class CycleCost:
    estimated_usd: float
    actual_usd: float
    duration_ms: int
    requests: int

    @property
    def variance_usd(self) -> float:
        return self.actual_usd - self.estimated_usd


def lambda_usd(*, duration_ms: int, memory_mb: int = DEFAULT_MEMORY_MB, requests: int = 1) -> float:
    gb_seconds = (memory_mb / 1024) * (duration_ms / 1000) * requests
    return gb_seconds * GB_SECOND_USD + requests * REQUEST_USD


def cycle_cost(
    *,
    runtime_ms: int,
    broker_ms: int,
    estimated_usd: float = 0.0,
    runtime_memory_mb: int = DEFAULT_MEMORY_MB,
    broker_memory_mb: int = DEFAULT_MEMORY_MB,
) -> CycleCost:
    """One capability cycle: runtime wake + broker execute. Heartbeat sink omitted."""
    actual = lambda_usd(duration_ms=runtime_ms, memory_mb=runtime_memory_mb) + lambda_usd(
        duration_ms=broker_ms, memory_mb=broker_memory_mb
    )
    return CycleCost(
        estimated_usd=estimated_usd,
        actual_usd=actual,
        duration_ms=runtime_ms + broker_ms,
        requests=2,
    )
