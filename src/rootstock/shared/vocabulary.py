"""Capability *names*.

Naming a capability here does not grant it. Declaration and grant are separate concerns
(docs/design/02-capability-model.md): the grant store is the sole authority on what any
actor may invoke, it is read-only to the runtime (AR-6), and nothing in this module confers
authority. These constants exist so code and tests can refer to ids without stringly-typed
typos.

Names are hierarchical and stable: domain.service.action. The first segment is the trust
zone, which makes blast radius legible at a glance.
"""

from __future__ import annotations

from typing import Final

MEMORY_READ: Final = "memory.read"
MEMORY_WRITE: Final = "memory.write"
SANDBOX_S3_CREATE_BUCKET: Final = "sandbox.s3.create_bucket"
SANDBOX_S3_PUT_OBJECT: Final = "sandbox.s3.put_object"
SANDBOX_S3_LIST: Final = "sandbox.s3.list"
SANDBOX_LOGS_READ: Final = "sandbox.logs.read"

DECLARED_AT_V0: Final[frozenset[str]] = frozenset(
    {
        MEMORY_READ,
        MEMORY_WRITE,
        SANDBOX_S3_CREATE_BUCKET,
        SANDBOX_S3_PUT_OBJECT,
        SANDBOX_S3_LIST,
        SANDBOX_LOGS_READ,
    }
)
"""The entire 0.0 vocabulary. An id outside this set is unroutable, not merely denied."""

SANDBOX_BUCKET_PREFIX: Final = "rootstock-sbx-"
"""Applied by the executor. Callers supply a suffix, never a whole bucket name (AR-16)."""
