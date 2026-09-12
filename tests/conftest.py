"""Keep the default suite off the operator's AWS credentials."""

from __future__ import annotations

import os

for _name in (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_PROFILE",
    "AWS_DEFAULT_PROFILE",
):
    os.environ.pop(_name, None)
