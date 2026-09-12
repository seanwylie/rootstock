"""No-credentials smoke: the public tree must run without an AWS account."""

from __future__ import annotations

import json
import os
from pathlib import Path

from check_aws_context import ACCOUNTS_FILE, load_accounts

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "infra" / "accounts.example.json"


def test_shipped_account_map_is_the_placeholder_example() -> None:
    assert ACCOUNTS_FILE.name == "accounts.json"
    gitignore = (ROOT / ".gitignore").read_text()
    assert "infra/accounts.json" in gitignore
    tracked_example = json.loads(EXAMPLE.read_text())
    assert tracked_example["profiles"]["rootstock-core"]["account_id"] == "111111111111"
    assert tracked_example["profiles"]["rootstock-sandbox"]["account_id"] == "022222222222"


def test_unit_suite_has_no_ambient_aws_credentials() -> None:
    assert not os.environ.get("AWS_ACCESS_KEY_ID")
    assert not os.environ.get("AWS_SECRET_ACCESS_KEY")
    assert not os.environ.get("AWS_SESSION_TOKEN")
    assert not os.environ.get("AWS_PROFILE")


def test_example_map_loads_without_network() -> None:
    accounts = load_accounts(EXAMPLE)
    assert accounts.profile_for_zone("sandbox") == "rootstock-sandbox"
    assert "default" in accounts.forbidden
    assert "management" not in {entry["zone"] for entry in accounts.profiles.values()}


def test_tfvars_example_has_no_operator_email() -> None:
    text = (ROOT / "infra" / "v0" / "terraform.tfvars.example").read_text()
    assert "ops@example.com" in text
    assert "@gmail.com" not in text
