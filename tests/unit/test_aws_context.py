"""The guard's refusal logic, tested without touching AWS.

Everything here runs before any network call, which is the part that has to be right: a
guard that only works once credentials are valid has already let the wrong terminal through.

Unit tests load `infra/accounts.example.json`, not the operator-local `accounts.json`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from check_aws_context import (
    ACCOUNTS_FILE,
    SSO_ROLE_PATTERN,
    Accounts,
    WrongContextError,
    load_accounts,
    resolve_profile,
)

EXAMPLE_FILE = ACCOUNTS_FILE.with_name("accounts.example.json")
SANDBOX_ACCOUNT = "022222222222"
CORE_ACCOUNT = "111111111111"


@pytest.fixture
def accounts() -> Accounts:
    return load_accounts(EXAMPLE_FILE)


class TestAccountMap:
    def test_known_profiles_and_ids(self, accounts: Accounts) -> None:
        assert accounts.profiles["rootstock-sandbox"]["account_id"] == SANDBOX_ACCOUNT
        assert accounts.profiles["rootstock-core"]["account_id"] == CORE_ACCOUNT

    def test_sandbox_leading_zero_survives(self, accounts: Accounts) -> None:
        # The whole reason account ids are strings. As a number this becomes 22222222222,
        # an eleven-digit id that resolves to nothing or, worse, to somebody else.
        raw = json.loads(EXAMPLE_FILE.read_text())
        assert raw["profiles"]["rootstock-sandbox"]["account_id"] == SANDBOX_ACCOUNT
        assert accounts.profiles["rootstock-sandbox"]["account_id"].startswith("0")

    def test_management_has_no_profile(self, accounts: Accounts) -> None:
        # AR-1 and AR-2 expressed in configuration: no tooling here can target Management,
        # because there is no name for it to resolve.
        zones = {entry["zone"] for entry in accounts.profiles.values()}
        assert zones == {"core", "sandbox"}
        assert "management" not in zones

    def test_default_is_forbidden(self, accounts: Accounts) -> None:
        assert "default" in accounts.forbidden

    def test_sso_principals_required(self, accounts: Accounts) -> None:
        assert accounts.require_sso is True

    def test_non_string_account_id_is_rejected(self, tmp_path: Path) -> None:
        bad = tmp_path / "accounts.json"
        bad.write_text(
            json.dumps({"profiles": {"p": {"account_id": 22222222222, "zone": "sandbox"}}})
        )
        with pytest.raises(WrongContextError, match="must be a string"):
            load_accounts(bad)

    def test_malformed_account_id_is_rejected(self, tmp_path: Path) -> None:
        bad = tmp_path / "accounts.json"
        bad.write_text(json.dumps({"profiles": {"p": {"account_id": "12345", "zone": "sandbox"}}}))
        with pytest.raises(WrongContextError, match="12-digit"):
            load_accounts(bad)

    def test_missing_map_points_at_the_example(self, tmp_path: Path) -> None:
        missing = tmp_path / "accounts.json"
        with pytest.raises(WrongContextError, match=r"accounts\.example\.json"):
            load_accounts(missing)


class TestProfileResolution:
    def test_unset_profile_is_refused(
        self, accounts: Accounts, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("AWS_PROFILE", raising=False)
        with pytest.raises(WrongContextError, match="not set"):
            resolve_profile(accounts, None)

    def test_default_profile_is_refused_by_name(self, accounts: Accounts) -> None:
        # `default` is forbidden so an unrelated personal profile cannot be selected by habit.
        with pytest.raises(WrongContextError, match="forbidden"):
            resolve_profile(accounts, "default")

    def test_unknown_profile_is_refused(self, accounts: Accounts) -> None:
        with pytest.raises(WrongContextError, match="unknown"):
            resolve_profile(accounts, "some-other-profile")

    def test_known_profiles_resolve(self, accounts: Accounts) -> None:
        assert resolve_profile(accounts, "rootstock-sandbox") == "rootstock-sandbox"
        assert resolve_profile(accounts, "rootstock-core") == "rootstock-core"

    def test_explicit_argument_beats_environment(
        self, accounts: Accounts, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AWS_PROFILE", "default")
        assert resolve_profile(accounts, "rootstock-core") == "rootstock-core"

    def test_environment_is_used_when_no_argument(
        self, accounts: Accounts, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AWS_PROFILE", "rootstock-sandbox")
        assert resolve_profile(accounts, None) == "rootstock-sandbox"

    def test_refusal_names_the_valid_profiles(self, accounts: Accounts) -> None:
        with pytest.raises(WrongContextError) as caught:
            resolve_profile(accounts, "default")
        assert "rootstock-sandbox" in str(caught.value)
        assert "rootstock-core" in str(caught.value)

    @pytest.mark.parametrize(
        "var", ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"]
    )
    def test_ambient_keys_are_refused(
        self, accounts: Accounts, monkeypatch: pytest.MonkeyPatch, var: str
    ) -> None:
        # Terraform prefers these over --profile. Leaving them set is how a personal
        # default key would leak into a Rootstock apply.
        monkeypatch.setenv(var, "AKIAEXAMPLE")
        with pytest.raises(WrongContextError, match="Ambient credential"):
            resolve_profile(accounts, "rootstock-sandbox")


class TestPrincipalShape:
    @pytest.mark.parametrize(
        "arn",
        [
            f"arn:aws:sts::{SANDBOX_ACCOUNT}:assumed-role/AWSReservedSSO_RootstockAdministrator_<id>/operator",
            f"arn:aws:sts::{CORE_ACCOUNT}:assumed-role/AWSReservedSSO_RootstockAdministrator_<id>/operator",
        ],
    )
    def test_sso_assumed_roles_are_accepted(self, arn: str) -> None:
        assert SSO_ROLE_PATTERN.match(arn)

    @pytest.mark.parametrize(
        "arn",
        [
            "arn:aws:iam::999999999999:user/unrelated",
            f"arn:aws:iam::{SANDBOX_ACCOUNT}:user/someone",
            f"arn:aws:sts::{SANDBOX_ACCOUNT}:assumed-role/SomeOtherRole/session",
            f"arn:aws:iam::{SANDBOX_ACCOUNT}:root",
        ],
    )
    def test_non_sso_principals_are_rejected(self, arn: str) -> None:
        # The third case matters most: a correct account reached through a non-SSO role is
        # still the wrong kind of credential.
        assert not SSO_ROLE_PATTERN.match(arn)


class TestZoneMapping:
    def test_zone_lookup(self, accounts: Accounts) -> None:
        assert accounts.profile_for_zone("sandbox") == "rootstock-sandbox"
        assert accounts.profile_for_zone("core") == "rootstock-core"

    def test_unmapped_zone_raises(self, accounts: Accounts) -> None:
        with pytest.raises(WrongContextError, match="No profile is mapped"):
            accounts.profile_for_zone("management")


def test_terraform_reads_the_same_file() -> None:
    # The guard and the provider must not disagree about which account is Sandbox.
    main_tf = (ACCOUNTS_FILE.parent / "test-env" / "main.tf").read_text()
    versions_tf = (ACCOUNTS_FILE.parent / "test-env" / "versions.tf").read_text()
    assert 'jsondecode(file("${path.module}/../accounts.json"))' in main_tf
    assert 'local.accounts.profiles["rootstock-sandbox"].account_id' in main_tf
    assert "profile = local.sandbox_profile" in versions_tf
    assert "allowed_account_ids = [local.sandbox_account_id]" in versions_tf
