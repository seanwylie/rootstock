# Phase 2 — Broker vertical slice

> **Verdict: complete.** All eight exit criteria passed. Criteria 1, 2, 3, 4, and 8 were
> observed live against Core + Sandbox. Criteria 5, 6, and 7 were observed in-process
> (deliberate AUDIT OPEN/CLOSE failure cannot be injected into real S3 without breaking
> AR-4). Replay (2) and AUDIT CLOSE → UNKNOWN (6) both pass. Ready for Phase 3.

## Commit / revision

```text
branch          main
base commit     adb37a3  ("Record Phase 0: harness, SSO guards, and first Sandbox cycle.")
working tree    uncommitted — Phase 1 substrate + Phase 2 broker slice
terraform       infra/v0, local state (not committed)
```

## Environment

```text
Python          3.12.3
uv              0.11.6
Terraform       1.9.8
AWS provider    5.100.0
AWS CLI         2.33.12
OS              Linux 7.0.0-30-generic
live test       2026-08-26T14:19Z     make v0-broker-live  (1 passed in 6.50s)
```

SSO sessions for both `rootstock-core` and `rootstock-sandbox` were already valid.

## Tests run

```text
ruff check / format                 pass
mypy --strict                       pass (37 source files)
pytest -m 'not destructive and not live'   pass (84 passed, 1 live deselected)
terraform fmt / validate            pass (test-env and infra/v0)
make v0-assert-iam                  pass
make v0-broker-live                 pass (1 passed)
```

Runtime still has no `sts:AssumeRole`. The IAM-negatives script never asserted RequestTag
on the Sandbox operator; those conditions were already gone when this re-run passed.

## Destructive tests run

**None.** D1–D8 remain unimplemented. Not required for Phase 2. Criterion 6 is the
in-process stand-in for D7's AUDIT CLOSE failure mode.

## AWS context resolved

```text
profile     rootstock-core
zone        core
account     111111111111
principal   arn:aws:sts::111111111111:assumed-role/AWSReservedSSO_RootstockAdministrator_<id>/operator

profile     rootstock-sandbox
zone        sandbox
account     022222222222
principal   arn:aws:sts::022222222222:assumed-role/AWSReservedSSO_RootstockAdministrator_<id>/operator
```

Live path: SSO → `rootstock-broker-role` (`Phase2FixtureAssume`) →
`RootstockSandboxOperatorRole` + per-invocation session policy. Ambient static keys were
stripped by the Makefile.

## Exit criteria

| # | Criterion | How | Result |
| --- | --- | --- | --- |
| 1 | Tagged bucket in Sandbox | Live: `HeadBucket` + `GetBucketTagging` after `broker.process` | pass |
| 2 | Replay → one bucket, one audit chain, `DUPLICATE` | Live + unit | pass |
| 3 | Undeclared capability rejected at ingress | Live + unit; no claim, no execute | pass |
| 4 | Out-of-scope denied, named rule | Live + unit; `scope.target` | pass |
| 5 | AUDIT OPEN failure blocks execution | Unit: `MemoryAudit(fail_open=True)` | pass |
| 6 | AUDIT CLOSE failure → `UNKNOWN`, claim non-terminal, incident | Unit: `MemoryAudit(fail_close=True)` | pass |
| 7 | Reconciliation closes `UNKNOWN` from the provider | Unit: retry after CLOSE works | pass |
| 8 | Session narrower than role ceiling | Live: scoped session `PutObject` denied; unit: actions/resources | pass |

Live tags observed: `rootstock:managed-by=rootstock`, `rootstock:purpose=phase2-live` (plus
`environment` and `owner` written by the executor). The test deletes the bucket afterward.

Audit ids are S3 `VersionId` values, not keys (Phase 1 object-lock finding).

## Observed results

- Schema → policy → claim → AUDIT OPEN → STS assume with session policy → `CreateBucket` +
  `PutBucketTagging` → AUDIT CLOSE is the live path. Prefix `rootstock-sbx-` is applied by
  the executor from a caller-supplied suffix (AR-16).
- Session policy template lives at `session-policies/sandbox.s3.create_bucket.json` in the
  grant store. The only runtime substitution is `{{bucket_arn}}`.
- `REQUIRE_APPROVAL` writes the approval store and returns `Outcome.DENIED` with
  `error.code=AWAITING_APPROVAL`. There is no `PARKED` outcome in the vocabulary.
  `sandbox.s3.create_bucket` is L3 and does not hit this path.
- AUDIT OPEN failure expires the lease rather than `DeleteItem` (broker IAM has no
  `DeleteItem` on claims). Retry can reclaim.
- Grant-store `GetObject` of a missing session-policy key must not be used as a probe:
  without `ListBucket`, a 404 is reported as `AccessDenied`. The adapter loads only the
  authored create-bucket template.

## Cost

One Sandbox bucket created and deleted per live run, two audit objects (OPEN + CLOSE) left
in object lock, one claims row. No Lambda, no model. Effectively $0.

## Deviations from plan

1. **No broker Lambda.** Fixtures assume `rootstock-broker-role` via a temporary trust
   statement `Phase2FixtureAssume` (Core SSO `RootstockAdministrator`). Remove in Phase 3
   when Lambda is the only caller. Sandbox operator trust is unchanged: broker-role only,
   `ExternalId` + `aws:PrincipalOrgID`.
2. **Create-then-tag, not tagged-at-CreateBucket.** S3 `CreateBucket` does not accept the
   tags in a way IAM can see. The executor calls `PutBucketTagging` immediately after.
3. **`aws:RequestTag` conditions removed** from the Sandbox operator policy (applied in
   Phase 1, taken off in Phase 2). See design finding.
4. Failed live attempts left four `UNKNOWN` claims whose buckets were already deleted.
   Those rows were removed at close-out, as was the successful live test's `EXECUTED` row
   (its bucket had already been deleted by test teardown). Audit OPEN/CLOSE objects remain
   (WORM).

## Design findings

### S3 does not populate `aws:RequestTag` (AR-13 at the IAM layer)

`docs/design/03-runtime-and-broker.md` specified RequestTag conditions on `CreateBucket` so
an untagged bucket could not be created. Reality:

- `iam:SimulatePrincipalPolicy` with RequestTag context reports **allowed**.
- Live `CreateBucket` with the same conditions is **implicit deny**.
- Live `PutBucketTagging` with RequestTag conditions is also **implicit deny**, even though
  simulate reports allowed.

AR-13 in `00-system-boundaries.md` already names "tagging policy plus reconciliation
sweep." The 03 IAM-layer claim is false for S3 buckets and has been corrected there.
Enforcement at 0.0 is: executor writes the four `rootstock:*` tags immediately after create;
the live test reads them back. The create-then-tag window can leave an untagged
`rootstock-sbx-*` bucket if the process dies between the calls. A sweep is load-bearing,
not optional. Session policy still excludes `PutObject` and logs, so AR-7 narrowing holds.

### `PutBucketTagging` is part of `sandbox.s3.create_bucket`, not a new capability

Callers still send a suffix and a purpose. Tagging is an executor detail required because
the provider API cannot do atomic tagged create. The session policy for this capability
includes `CreateBucket`, `PutBucketTagging`, and `ListBucket` on one bucket ARN.

## Blocker encountered

IAM policy updates are not instantly visible to assumed sessions. After removing RequestTag
from `PutBucketTagging`, the next live run still denied until the policy had propagated
(~10s). Simulate was a false friend throughout: it cannot substitute for a live S3 call
when the question is which condition keys the API actually sends.

## Ready for Phase 3

Yes. Exit criteria 2 (replay) and 6 (AUDIT CLOSE → UNKNOWN) both pass. Do not start Phase 3
until `Phase2FixtureAssume` has a removal ticket in that phase's work: the runtime Lambda
must be the only principal that can assume the broker role.
