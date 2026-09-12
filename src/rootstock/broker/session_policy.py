"""Session policy for one invocation. Authored, then bound to a specific resource (AR-7)."""

from __future__ import annotations

import copy
from typing import Any


def bind_session_policy(template: dict[str, Any], *, bucket_arn: str) -> dict[str, Any]:
    """Substitute the bucket ARN into an authored session policy.

    Generated IAM is hard to review; the grant store holds the template, and the only
    runtime substitution is the resource this request is allowed to touch.
    """
    bound = copy.deepcopy(template)

    def _walk(node: Any) -> Any:
        if isinstance(node, str):
            return node.replace("{{bucket_arn}}", bucket_arn)
        if isinstance(node, list):
            return [_walk(item) for item in node]
        if isinstance(node, dict):
            return {key: _walk(value) for key, value in node.items()}
        return node

    result = _walk(bound)
    assert isinstance(result, dict)
    return result
