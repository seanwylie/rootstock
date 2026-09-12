#!/usr/bin/env python3
"""Ask Sandbox what Rootstock resources exist, independently of Terraform state.

Phase 0 exit criterion 3. Terraform reporting a clean destroy is Terraform's opinion about
its own state file; this asks the provider. The two disagree whenever something was created
outside Terraform -- which, from Phase 2 onward, is exactly what the broker does.

--expect absent  (default): fail if any rootstock-sbx-* bucket remains
--expect present: fail if none exist -- used after apply, so create is also observed

Exit codes:
    0  expectation met
    1  expectation not met
    2  harness problem (no credentials, wrong account)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_aws_context import (
    WrongContextError,
    check_identity,
    load_accounts,
    resolve_profile,
)

PREFIX = "rootstock-sbx-"
EXIT_CLEAN = 0
EXIT_DIRTY = 1
EXIT_HARNESS = 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", default=PREFIX, help=f"bucket prefix (default {PREFIX})")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--profile", help="override $AWS_PROFILE")
    parser.add_argument(
        "--expect",
        choices=("absent", "present"),
        default="absent",
        help="absent: teardown check (default). present: apply must have left a bucket.",
    )
    args = parser.parse_args()

    # Same guard the Makefile runs. Sweeping the wrong account and reporting "clean" would be
    # a false negative on a teardown check, which is worse than failing outright.
    try:
        accounts = load_accounts()
        profile = resolve_profile(accounts, args.profile)
        context = check_identity(accounts, profile, expect_zone="sandbox")
    except WrongContextError as exc:
        print(f"\nAWS context check FAILED\n\n{exc}\n", file=sys.stderr)
        return EXIT_HARNESS

    account = context["account"]

    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError

        session = boto3.Session(profile_name=profile)
        buckets = session.client("s3", region_name=args.region).list_buckets()["Buckets"]
    except (BotoCoreError, ClientError) as exc:
        print(f"Could not list buckets: {exc}", file=sys.stderr)
        return EXIT_HARNESS

    remaining = sorted(b["Name"] for b in buckets if b["Name"].startswith(args.prefix))

    if args.expect == "present":
        if not remaining:
            print(
                f"Apply not observed: no {args.prefix}* buckets in account {account}. "
                "Terraform may have reported success against a different reality."
            )
            return EXIT_DIRTY
        print(f"Presence verified: {len(remaining)} resource(s) in {account}.")
        for name in remaining:
            print(f"  s3://{name}")
        return EXIT_CLEAN

    if remaining:
        print(f"Teardown incomplete: {len(remaining)} resource(s) remain in {account}.")
        for name in remaining:
            print(f"  s3://{name}")
        return EXIT_DIRTY

    print(f"Teardown verified: no {args.prefix}* resources in account {account}.")
    return EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
