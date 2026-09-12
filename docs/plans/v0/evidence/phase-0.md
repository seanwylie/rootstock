# Phase 0 — Test harness

> **Verdict: complete.** All three exit criteria passed. First real Sandbox mutation
> observed, then independently confirmed gone. Ready for Phase 1.

Raw Terraform/CLI transcript: [`phase-0-infra-cycle.log`](phase-0-infra-cycle.log).

## Commit / revision

```text
branch          main
commit          adb37a3  ("Record Phase 0: harness, SSO guards, and first Sandbox cycle.")
terraform       infra/test-env, local state, empty after destroy (0 resources)
```

## Environment

```text
Python          3.12.3
uv              0.11.6
Terraform       1.9.8
AWS provider    5.100.0
AWS CLI         2.33.12
OS              Linux 7.0.0-30-generic
run started     2026-08-26T04:47:48Z
cycle started   2026-08-26T04:47:57Z
cycle ended     2026-08-26T04:48:33Z
elapsed         36s for two apply/destroy cycles
```

## Tests run

```text
ruff check src tests scripts        pass
mypy --strict                       pass (21 source files)
pytest -q                           pass (66 passed)
terraform fmt / validate            pass
make aws-context                    pass
make aws-context-core               pass
make infra-init                     exit 0
make infra-plan                     exit 0
make infra-cycle                    exit 0
make verify-teardown (final)        exit 0
aws s3api list-buckets (prefix)     []
```

## Destructive tests run

**None.** Registry still has D1–D8 unimplemented. Not required for Phase 0.

## AWS context resolved

```text
profile     rootstock-sandbox
zone        sandbox
account     022222222222
principal   arn:aws:sts::022222222222:assumed-role/AWSReservedSSO_RootstockAdministrator_<id>/operator
```

`data.aws_caller_identity.current` during plan/apply returned the same account id. The
Terraform `account_guard` precondition passed. An unrelated personal `default` profile
was never used.

## Resource created

```text
bucket      rootstock-sbx-phase0-harness
account     022222222222
region      us-east-1
tags        rootstock:environment=test
            rootstock:managed-by=terraform
            rootstock:owner=rootstock
            rootstock:purpose=phase-0-harness
```

Each apply created 4 resources: the bucket, public-access block, versioning config
(`Disabled`), and `terraform_data.account_guard`.

Independent inventory after each apply (`make verify-presence`, S3 ListBuckets, not
Terraform state):

```text
Presence verified: 1 resource(s) in 022222222222.
  s3://rootstock-sbx-phase0-harness
```

Observed twice, once per cycle.

## Resource destroyed

Each destroy reported `Destroy complete! Resources: 4 destroyed.`

Independent inventory after each destroy (`make verify-teardown`, S3 ListBuckets):

```text
Teardown verified: no rootstock-sbx-* resources in account 022222222222.
```

Observed twice during the cycle, and a third time after the cycle returned. A direct
`aws s3api list-buckets` query for the prefix also returned `[]`. Terraform state shows
0 resources.

**Teardown proof is the provider inventory, not the destroy exit code.**

## Exit codes

| Step | Exit |
| --- | --- |
| `make aws-context` | 0 |
| `make infra-init` | 0 |
| `make infra-plan` | 0 |
| apply 1 | 0 (4 added) |
| verify-presence 1 | 0 |
| destroy 1 | 0 (4 destroyed) |
| verify-teardown 1 | 0 |
| apply 2 | 0 (4 added) |
| verify-presence 2 | 0 |
| destroy 2 | 0 (4 destroyed) |
| verify-teardown 2 | 0 |
| `make infra-cycle` overall | 0 |
| final independent inventory | 0 |

## Cost observations

**$0.00 incremental.** Empty S3 buckets in us-east-1 have no storage charge. Standing
infrastructure after the cycle: none.

## Deviations from plan

1. **`src/` layout** instead of flat top-level packages. Plan-level; no architectural impact.
2. **Terraform installed to `~/.local/bin`.** Not present on the machine.
3. **Account IDs encoded in `infra/accounts.json`**, not operator-supplied tfvars.
4. **`make infra-cycle` now verifies presence after apply**, not only absence after destroy.
   Without that, a no-op apply plus a clean destroy would have satisfied the original
   Makefile while never mutating Sandbox.
5. **Ambient-key rejection and SSO-principal checks** were added before the cycle, after
   the two SSO profiles existed.

## Design findings

### F-1 — The claim state machine has no state for an approval-parked request

**Resolved 2026-08-26** in `docs/design/03-runtime-and-broker.md`.

The claim table is for execution only (`PENDING` means a lease is held). `REQUIRE_APPROVAL`
goes to a separate `rootstock-approvals` table with no lease. Policy evaluates before any
claim is taken, so "please wait" cannot occupy `PENDING`. VERIFY's parked path is a lookup
in the approval store.

## Surprise behavior

None material.

- The cycle was fast (36s). S3 create/delete of an empty bucket in us-east-1 was ~1s each.
- Default tags landed on `tags_all` as specified. The bucket's own `tags` attribute stayed
  empty; that is AWS-provider behavior for `default_tags`, not a tagging failure.
- Provider 5.100.0 was already in the lock file from an earlier `init -backend=false`.
- No retry, no eventual-consistency miss: presence and absence checks succeeded immediately
  after apply and destroy.

## Exit criteria verdict

| # | Criterion | Verdict |
| --- | --- | --- |
| 1 | `terraform apply` and `destroy` run clean, twice in a row | **PASS** |
| 2 | A fixture submitting to a non-existent component fails with a clear error | **PASS** |
| 3 | Teardown verified by listing Sandbox and finding zero `rootstock-sbx-*` | **PASS** |

Phase 0 is complete. Phase 1 is complete. F-1 is resolved and does not block Phase 2.
