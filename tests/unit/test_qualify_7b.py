"""7b cost guard: never run Terra while EventBridge is enabled."""

from __future__ import annotations

import pytest
from qualify_7b import refuse_if_wake_enabled


def test_refuse_if_wake_enabled() -> None:
    with pytest.raises(SystemExit, match="supervised invokes only"):
        refuse_if_wake_enabled("ENABLED")
    refuse_if_wake_enabled("DISABLED")
