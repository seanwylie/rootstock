"""Execute one capability under a scoped session. Holds credentials; the model never does."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from rootstock.broker.errors import ExecuteError
from rootstock.shared.vocabulary import SANDBOX_BUCKET_PREFIX


@dataclass(frozen=True, slots=True)
class ExecuteResult:
    bucket: str
    tags: dict[str, str]


class Executor(Protocol):
    def create_bucket(
        self,
        *,
        suffix: str,
        purpose: str,
        canonical_id: str,
        session_policy: dict[str, Any],
    ) -> ExecuteResult: ...

    def bucket_exists(self, bucket: str) -> bool: ...

    def last_session_policy(self) -> dict[str, Any] | None: ...


def bucket_name(suffix: str) -> str:
    return f"{SANDBOX_BUCKET_PREFIX}{suffix}"


@dataclass
class FakeExecutor:
    """In-process provider. Records the session policy so tests can assert narrowing."""

    buckets: set[str] = field(default_factory=set)
    tags: dict[str, dict[str, str]] = field(default_factory=dict)
    fail_after_side_effect: bool = False
    calls: int = 0
    session_policies: list[dict[str, Any]] = field(default_factory=list)

    def create_bucket(
        self,
        *,
        suffix: str,
        purpose: str,
        canonical_id: str,
        session_policy: dict[str, Any],
    ) -> ExecuteResult:
        del canonical_id
        name = bucket_name(suffix)
        self.calls += 1
        self.session_policies.append(session_policy)
        applied = {
            "rootstock:managed-by": "rootstock",
            "rootstock:purpose": purpose,
            "rootstock:environment": "v0",
            "rootstock:owner": "rootstock",
        }
        self.buckets.add(name)
        self.tags[name] = applied
        if self.fail_after_side_effect:
            raise ExecuteError(
                "provider call completed; confirmation lost",
                side_effect_likely=True,
            )
        return ExecuteResult(bucket=name, tags=applied)

    def bucket_exists(self, bucket: str) -> bool:
        return bucket in self.buckets

    def last_session_policy(self) -> dict[str, Any] | None:
        return self.session_policies[-1] if self.session_policies else None
