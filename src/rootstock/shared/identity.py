"""Canonical request identity (AR-15).

The runtime supplies an idempotency key. The broker derives the id. A caller-chosen opaque
id could be varied to evade deduplication; a derived id makes identical intents collide.
"""

from __future__ import annotations

import hashlib

from rootstock.shared.canonical import canonical_json
from rootstock.shared.capability import CapabilityRequest


def canonical_request_id(request: CapabilityRequest) -> str:
    """sha256 of idempotency_key, capability, target, and canonical parameters.

    Encoded as canonical JSON of a four-element array so the concatenation is unambiguous
    (a raw ``‖`` join would be injectable if a field contained the separator).
    """
    blob = canonical_json(
        [
            request.idempotency_key,
            request.capability,
            request.target,
            request.parameters,
        ]
    )
    return hashlib.sha256(blob).hexdigest()
