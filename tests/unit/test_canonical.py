"""canonical_json feeds the canonical request id, so determinism here is a safety property."""

from __future__ import annotations

import pytest

from rootstock.shared.canonical import NonCanonicalValueError, canonical_json


def test_key_order_does_not_affect_output() -> None:
    a = canonical_json({"b": 1, "a": 2, "c": {"z": 1, "y": 2}})
    b = canonical_json({"c": {"y": 2, "z": 1}, "a": 2, "b": 1})
    assert a == b


def test_no_insignificant_whitespace() -> None:
    assert canonical_json({"a": 1, "b": [1, 2]}) == b'{"a":1,"b":[1,2]}'


def test_unicode_is_not_escaped() -> None:
    # ensure_ascii=False keeps the byte encoding stable and readable; the important part is
    # that it is *consistent*, since these bytes are hashed.
    assert canonical_json({"k": "café"}) == '{"k":"café"}'.encode()


def test_list_order_is_preserved() -> None:
    # Lists are ordered data. Sorting them would silently merge distinct requests.
    assert canonical_json([3, 1, 2]) != canonical_json([1, 2, 3])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_floats_are_rejected(value: float) -> None:
    # json.dumps would otherwise emit bare NaN/Infinity tokens, producing a stable hash for
    # a document no parser will read back.
    with pytest.raises(NonCanonicalValueError):
        canonical_json({"cost": value})


def test_non_string_keys_are_rejected() -> None:
    with pytest.raises(NonCanonicalValueError):
        canonical_json({1: "a"})  # type: ignore[dict-item]


def test_unsupported_types_are_rejected() -> None:
    with pytest.raises(NonCanonicalValueError):
        canonical_json({"when": object()})


def test_error_names_the_path() -> None:
    with pytest.raises(NonCanonicalValueError, match=r"\$\.outer\.inner"):
        canonical_json({"outer": {"inner": object()}})
