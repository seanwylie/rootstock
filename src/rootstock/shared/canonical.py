"""Deterministic serialisation.

Output feeds the canonical request id (AR-15), so two logically identical requests must
serialise byte-identically on any machine, in any Python build, in any order of construction.
"""

from __future__ import annotations

import json
import math
from typing import Any

JsonValue = None | bool | int | float | str | list[Any] | dict[str, Any]


class NonCanonicalValueError(ValueError):
    """A value that has no single unambiguous serialisation."""


def _check(value: object, path: str = "$") -> None:
    if value is None or isinstance(value, bool | int | str):
        return
    if isinstance(value, float):
        # NaN and infinities are not representable in JSON, and json.dumps emits bare
        # NaN/Infinity tokens for them rather than failing. Two runs could then agree on a
        # hash for a value that no parser will read back.
        if math.isnan(value) or math.isinf(value):
            raise NonCanonicalValueError(f"{path}: non-finite float {value!r}")
        return
    if isinstance(value, list):
        for i, item in enumerate(value):
            _check(item, f"{path}[{i}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise NonCanonicalValueError(f"{path}: non-string key {key!r}")
            _check(item, f"{path}.{key}")
        return
    raise NonCanonicalValueError(f"{path}: unsupported type {type(value).__name__}")


def canonical_json(value: JsonValue) -> bytes:
    """Serialise to canonical UTF-8 JSON.

    Sorted keys, no insignificant whitespace, no non-finite floats, no non-string keys.
    Rejects rather than coerces: a value that cannot be canonicalised is a bug in the caller,
    and silently accepting it would produce a hash that does not mean what it claims.
    """
    _check(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
