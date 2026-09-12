#!/usr/bin/env python3
"""Refuse to act unless AWS credentials resolve to the expected Rootstock account.

Rootstock tooling must never use ambient credentials. A machine often has a `default`
profile pointing at an unrelated account, and the failure this guard prevents is not
exotic: it is running `terraform apply` in the wrong terminal.

Four things are checked, and all four must hold:

1. The profile is named explicitly and is one this repository knows about. `default` is
   rejected by name, and so is anything absent from infra/accounts.json.
2. Ambient static keys are absent. `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` take
   precedence over a named profile in both boto3 and the Terraform AWS provider, so leaving
   them set would silently substitute the personal `default` credentials.
3. The resolved account id matches the one mapped to that profile.
4. The principal is an assumed SSO role, not an IAM user. A static access key satisfying
   checks 1 and 3 would still be the wrong kind of credential -- "Rootstock gets an
   identity, not a password".

Exit codes:
    0  context is correct
    2  context is wrong or could not be established
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, NamedTuple

ACCOUNTS_FILE = Path(__file__).resolve().parent.parent / "infra" / "accounts.json"
PROFILE_ENV = "AWS_PROFILE"
AMBIENT_KEY_VARS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN")
EXIT_OK = 0
EXIT_WRONG_CONTEXT = 2

ACCOUNT_ID_PATTERN = re.compile(r"^[0-9]{12}$")
SSO_ROLE_PATTERN = re.compile(r"^arn:aws:sts::[0-9]{12}:assumed-role/AWSReservedSSO_")


class WrongContextError(Exception):
    """The active AWS context is not one this repository is allowed to act in."""


class Accounts(NamedTuple):
    profiles: dict[str, dict[str, str]]
    forbidden: frozenset[str]
    require_sso: bool

    def zone_of(self, profile: str) -> str:
        return self.profiles[profile]["zone"]

    def profile_for_zone(self, zone: str) -> str:
        for name, entry in self.profiles.items():
            if entry["zone"] == zone:
                return name
        raise WrongContextError(
            f"No profile is mapped to zone {zone!r}. Known zones: "
            f"{', '.join(sorted(e['zone'] for e in self.profiles.values()))}"
        )


def load_accounts(path: Path = ACCOUNTS_FILE) -> Accounts:
    try:
        raw: dict[str, Any] = json.loads(path.read_text())
    except FileNotFoundError as exc:
        example = path.with_name("accounts.example.json")
        raise WrongContextError(
            f"Account map missing at {path}.\n"
            f"Copy {example} to {path} and put the operator's account ids there."
        ) from exc

    profiles: dict[str, dict[str, str]] = raw["profiles"]

    for name, entry in profiles.items():
        account_id = entry["account_id"]
        if not isinstance(account_id, str):
            # A leading zero survives only as a string. Catching this here beats debugging a
            # provider that silently targeted account 22222222222.
            raise WrongContextError(
                f"Profile {name!r}: account_id must be a string, got {type(account_id).__name__}"
            )
        if not ACCOUNT_ID_PATTERN.match(account_id):
            raise WrongContextError(
                f"Profile {name!r}: {account_id!r} is not a 12-digit account id"
            )

    return Accounts(
        profiles=profiles,
        forbidden=frozenset(raw.get("forbidden_profiles", ())),
        require_sso=bool(raw.get("require_sso_principal", True)),
    )


def refuse_ambient_keys() -> None:
    """Static env keys override --profile in Terraform. They must not be present."""
    present = [name for name in AMBIENT_KEY_VARS if os.environ.get(name)]
    if present:
        listed = ", ".join(present)
        raise WrongContextError(
            f"Ambient credential environment variable(s) set: {listed}.\n"
            "These override a named profile in Terraform and boto3, which is how a\n"
            "personal `default` key leaks into a Rootstock command.\n"
            "  unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN\n"
            "  export AWS_PROFILE=rootstock-sandbox   # or rootstock-core"
        )


def resolve_profile(accounts: Accounts, explicit: str | None) -> str:
    refuse_ambient_keys()
    profile = explicit or os.environ.get(PROFILE_ENV)
    known = ", ".join(sorted(accounts.profiles))

    if not profile:
        raise WrongContextError(
            f"{PROFILE_ENV} is not set.\n"
            "Rootstock tooling never uses ambient credentials -- name the account you mean.\n"
            f"  export AWS_PROFILE=<{known}>"
        )
    if profile in accounts.forbidden:
        raise WrongContextError(
            f"Profile {profile!r} is forbidden for Rootstock tooling.\n"
            "It resolves to personal or unrelated credentials.\n"
            f"  export AWS_PROFILE=<{known}>"
        )
    if profile not in accounts.profiles:
        raise WrongContextError(
            f"Profile {profile!r} is unknown to this repository.\nKnown: {known}"
        )
    return profile


def check_identity(accounts: Accounts, profile: str, expect_zone: str | None) -> dict[str, str]:
    entry = accounts.profiles[profile]

    if expect_zone and entry["zone"] != expect_zone:
        raise WrongContextError(
            f"Profile {profile!r} targets the {entry['zone']!r} zone, "
            f"but this operation requires {expect_zone!r}.\n"
            f"  export AWS_PROFILE={accounts.profile_for_zone(expect_zone)}"
        )

    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as exc:
        raise WrongContextError("boto3 is not installed. Run: uv sync --extra dev") from exc

    try:
        session = boto3.Session(profile_name=profile)
        identity = session.client("sts").get_caller_identity()
    except (BotoCoreError, ClientError) as exc:
        raise WrongContextError(
            f"Could not establish identity for profile {profile!r}.\n"
            f"  aws sso login --profile {profile}\n"
            f"Underlying error: {type(exc).__name__}: {exc}"
        ) from exc

    account = str(identity["Account"])
    arn = str(identity["Arn"])
    expected = entry["account_id"]

    if account != expected:
        raise WrongContextError(
            f"Profile {profile!r} resolved to account {account}, expected {expected}.\n"
            "Either the profile is misconfigured or infra/accounts.json is stale. "
            "Resolve before acting -- do not override."
        )

    if accounts.require_sso and not SSO_ROLE_PATTERN.match(arn):
        raise WrongContextError(
            f"Principal {arn} is not an assumed SSO role.\n"
            "Rootstock tooling requires temporary Identity Center credentials, not a static\n"
            "IAM user or access key, even when the account id happens to be correct."
        )

    return {"profile": profile, "account": account, "arn": arn, "zone": entry["zone"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", help=f"override ${PROFILE_ENV}")
    parser.add_argument("--expect", dest="expect_zone", choices=["core", "sandbox"])
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    try:
        accounts = load_accounts()
        profile = resolve_profile(accounts, args.profile)
        context = check_identity(accounts, profile, args.expect_zone)
    except WrongContextError as exc:
        print(f"\nAWS context check FAILED\n\n{exc}\n", file=sys.stderr)
        return EXIT_WRONG_CONTEXT

    if not args.quiet:
        print(
            f"AWS context OK: profile={context['profile']} "
            f"zone={context['zone']} account={context['account']}"
        )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
