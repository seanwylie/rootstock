# Phase 5 — Adversarial validation

> **Verdict: complete.** All eight destructive tests pass, are automated, and restore
> even on failure. Every Sandbox `CreateBucket` in the test window joins a claim by STS
> session name (`canonical_id`). Cost per cycle is ~$0.000036 with estimate $0.00.
> Ready for Phase 6. Do not enable the wake rule.

## Commit / revision

```text
branch          main
base commit     4330d8a  ("Record Phase 3 runtime and Phase 4 liveness.")
working tree    Phase 5 (this record)
terraform       infra/v0, local state (not committed); no apply this phase
```

## Environment

```text
Python          3.12.3
uv              0.11.6
Terraform       1.9.8
AWS CLI         2.33.12
OS              Linux 7.0.0-30-generic
live test       2026-08-26T16:06:54Z  make v0-destructive-live  (10 passed in 295.14s)
```

SSO sessions for both `rootstock-core` and `rootstock-sandbox` were already valid.

## Tests run

```text
ruff check / format                 pass
mypy --strict                       pass (55 source files)
pytest -m 'not destructive and not live'   pass (104 passed, 16 deselected)
terraform fmt                       pass
make v0-destructive-live            pass (10 passed)
make destructive-list               all eight implemented
```

## Destructive tests run

All eight, live, via `tests/destructive/runner.py` bodies in `tests/destructive/cases.py`.
Restore runs in `finally`.

| ID | Break | Observed | Result |
| --- | --- | --- | --- |
| D1 | Runtime reserved concurrency 0 | Watch returns `silent=true`, age ≥ 5s | pass |
| D2 | Overwrite `constitution.json` | VERIFY `halted` / `constitution_digest_mismatch`; restore then noop | pass |
| D3 | Simulate `sts:AssumeRole` from runtime | `implicitDeny` on sandbox operator and a Management-shaped ARN | pass |
| D4 | Replay identical create | One bucket; second `DUPLICATE`, same `audit_id` | pass |
| D5 | Undeclared capability `aws.call` | `REJECTED` / `schema.undeclared_capability` | pass |
| D6 | Target outside prefix | `DENIED` / `scope.target` | pass |
| D7 | Bucket policy Deny `s3:PutObject` on audit | `FAILURE` / `audit.open`; no bucket | pass |
| D8 | Bucket policy Deny on `close.json` | `UNKNOWN`, claim non-terminal, `incident=true`; reconcile → `SUCCESS` / `reconcile.provider` | pass |

## AWS context resolved

```text
profile     rootstock-core
zone        core
account     111111111111

profile     rootstock-sandbox
zone        sandbox
account     022222222222
```

Wake rule `rootstock-runtime-wake` remains `DISABLED`. Broker inline policies are
`rootstock-broker` only (Phase 5 deny policies deleted). Audit bucket has no leftover
Deny policy.

## Exit criteria

| # | Criterion | How | Result |
| --- | --- | --- | --- |
| 1 | All eight destructive tests pass, automated and repeatable | `make v0-destructive-live`; registry factories + `destructively()` restore | pass |
| 2 | Zero Sandbox mutations without a corresponding decision record | CloudTrail Event history: operator `CreateBucket` session name = `canonical_id`; claim row exists. 20-minute window had no orphans | pass |
| 3 | Cost per cycle known within a stable range | CloudWatch `AWS/Lambda` Duration; see Cost | pass |

## Observed results

- D1–D6 were already covered by earlier phase live tests; Phase 5 registers them in the
  destructive runner and re-runs them as break/assert/restore.
- D7 and D8 are the pair the plan flagged. Both fail in the specified direction against
  real S3, not `MemoryAudit`.
- CloudTrail join uses Event history `LookupEvents` in Sandbox. Session name is
  `canonical_id` (64 hex chars, fits `RoleSessionName`). No organization trail.

## Cost

```text
estimated_cost     $0.00  (stub; CapabilityRequest.estimated_cost)
runtime Duration   ~3.8–5.3 s  (256 MB, us-east-1 x86)
broker Duration    ~3.0–6.7 s  (256 MB)
representative     runtime 4501 ms + broker 3991 ms
actual             $0.00003578 / cycle
variance           $0.00003578  (estimate was zero)
stable range       well under $0.0001 / cycle; no model
```

List price used: $0.0000166667 / GB-second + $0.0000002 / request. Heartbeat sink and
silence watch are outside the cycle pair. There is still no ledger table; the figure lives
in this record and in CloudWatch.

## Deviations from plan

1. **D7/D8 revoke audit write via an S3 bucket policy, not by detaching the broker
   identity policy.** `iam:PutRolePolicy` Deny is visible to `SimulatePrincipalPolicy`
   immediately but S3 continued to allow (D7) or deny (D8 restore) for tens of seconds.
   A bucket policy Deny on the audit bucket takes effect on the next `PutObject`. The
   architectural claim is the same: without audit write, OPEN fails closed and CLOSE
   yields `UNKNOWN`.
2. **CloudTrail reconciliation used Event history, not an organization trail.** Lookup
   covers 90 days of management events without a trail. Durable multi-account trail is
   still unbuilt (`operations/aws-setup.md`).
3. **No ledger store.** Phase 1 did not create one. Cost is measured from Lambda metrics
   and recorded here, not appended to a Rootstock ledger.
4. **D2 tampers `constitution.json`, not `constitution.sha256`.** VERIFY hashes the S3
   body against deploy-time `CONSTITUTION_SHA256`. The grant-store digest object is unused
   at runtime.
5. **Wake stays DISABLED.**

## Design findings

### IAM identity-policy simulation is not a substitute for S3's evaluation lag

`SimulatePrincipalPolicy` on `rootstock-broker-role` reported Deny as soon as an inline
policy was attached, and Allowed as soon as it was deleted. The live `PutObject` to the
audit bucket did not match that timeline. Bucket policies (resource-based) matched live
behaviour. Anyone using IAM simulation as the wait condition for a live D7/D8 will
observe a false green (D7 executes) or a stuck `UNKNOWN` (D8 cannot close).

### `constitution.sha256` in the grant store is not the VERIFY input

Expected digest is Lambda environment, baked at apply. Changing only
`constitution.sha256` would not halt. VERIFY is still fail-closed against the body; the
unused digest object is a footgun if someone thinks overwriting it amends the constitution.

### Event history is enough to join v0 mutations, and is not an organization trail

Criterion 2 is mechanically checkable today because session name = `canonical_id`. It is
not a 90-day-plus org-wide audit architecture. That remains a later operations item and
does not block Phase 6.

## Blocker encountered

First D7 run created a bucket: identity Deny had not reached S3. First D8 restore left
`UNKNOWN` because identity Deny had not lifted. Switching to bucket policies and retrying
reconcile until CLOSE succeeds unblocked both.

## Ready for Phase 6

Yes. `D1`–`D8` pass with the stub. Sequence rule 2 is satisfied. Do not enable the wake
rule. Do not insert a model until this record is the baseline the model-swap must not
disturb.
