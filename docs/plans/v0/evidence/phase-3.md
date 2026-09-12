# Phase 3 — Runtime vertical slice

> **Verdict: complete.** All six exit criteria passed. Criteria 1, 2, 3, 5, and 6 were
> observed live against Core + Sandbox. Criterion 4 (`D3`) was observed by IAM simulation
> plus a source scan of `src/rootstock/runtime`. Ready for Phase 4.

## Commit / revision

```text
branch          main
base commit     8f7cbeb  ("Record Phase 1 substrate and the Phase 2 broker slice.")
working tree    uncommitted — Phase 3 runtime + broker Lambdas
terraform       infra/v0, local state (not committed)
lambda hash     M/wK36lzpuFdGqGtqTAlRCQQblnHOzMWQBSqxMCEWh4=
```

Live tests ran against the previous zip (`u7PptDem1Kip7pT8al5AzwL1zbVJdKoun2ItU0OykfQ=`).
The follow-up apply only deleted the unused Phase 2 `assume_broker_role` helper; loop
behaviour is unchanged.

## Environment

```text
Python          3.12.3
uv              0.11.6
Terraform       1.9.8
AWS provider    5.100.0
AWS CLI         2.33.12
OS              Linux 7.0.0-30-generic
live test       2026-08-26T14:56:36Z  make v0-runtime-live  (2 passed in 143.04s)
IAM negatives   2026-08-26T14:51Z     make v0-assert-iam
lambda apply    2026-08-26T15:00Z     0 add, 2 change (runtime + broker zip)
```

SSO sessions for both `rootstock-core` and `rootstock-sandbox` were already valid.

## Tests run

```text
ruff check / format                 pass
mypy --strict                       pass (46 source files)
pytest -m 'not destructive and not live'   pass (94 passed, 3 live deselected)
terraform fmt / validate            pass (test-env and infra/v0)
make v0-assert-iam                  pass (runtime AssumeRole implicitDeny)
make v0-runtime-live                pass (2 passed)
```

## Destructive tests run

**None.** `D1`–`D8` remain unimplemented. Criterion 4 is the IAM-simulation and source-scan
stand-in for `D3` (runtime cannot invoke a capability directly). Full `D3` belongs to
Phase 5.

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

Live path: EventBridge-shaped invoke of `rootstock-runtime` → SQS
`rootstock-capability-requests` → `rootstock-broker` (event source mapping, batch_size=1)
→ `RootstockSandboxOperatorRole` + per-invocation session policy. Ambient static keys were
stripped by the Makefile. Wake rule `rootstock-runtime-wake` remains `DISABLED`.

## Exit criteria

| # | Criterion | How | Result |
| --- | --- | --- | --- |
| 1 | Ten consecutive cycles, no human execution | Live: 10 runtime invokes, each decision closed by broker, `HeadBucket` on `rootstock-sbx-cycle-{n}` | pass |
| 2 | Cycle *N+1* observes *N*'s bucket; `expected_outcome` met | Live: second cycle of the ten returns `expected_outcome_met=True`. Unit: same with in-process harness | pass |
| 3 | Noop still writes a decision record | Live: `{"stub_mode":"noop"}` → `state=closed`, `opened_by=runtime`, `closed_by=runtime` | pass |
| 4 | Runtime cannot invoke a capability directly (`D3`) | IAM: `sts:AssumeRole` on sandbox operator and a Management-shaped ARN is `implicitDeny`. Source scan: no `assume_role(` under `src/rootstock/runtime` | pass |
| 5 | Kill broker → skip; expired lease → halt; distinguished | Unit: `FrozenClock` + injected `PENDING`. Live: reserved concurrency 0 + mapping disabled; skip then expired `PENDING` → `halted` / `prior_lease_expired` | pass |
| 6 | Two authors | Live: create cycles `opened_by=runtime`, `closed_by=broker`. Noop: both runtime | pass |

## Observed results

- VERIFY → OBSERVE → LEARN → `StubReasoner` → DECIDE → SQS → dormant is the live path.
  The runtime never waits for the broker. Cursor is `pk=runtime sk=cursor` in
  `rootstock-memory`.
- Observation is Core-only. The runtime cannot list Sandbox; inventory is reconstructed
  from closed decision artifacts (AR-2).
- Canonical id is `sha256` of canonical JSON `[idempotency_key, capability, target,
  parameters]`. Stub suffix is `cycle-{n}` → buckets `rootstock-sbx-cycle-{n}`.
- Enqueue-before-claim is skip, not halt: `verify_prior_cycle(..., enqueue_window_valid=True)`
  covers the gap after DECIDE and before the broker's `PENDING` lease (LEASE_SECONDS=180).
- `Phase2FixtureAssume` is gone. Broker-role trust is `lambda.amazonaws.com` only. Phase 2
  live now invokes the broker Lambda directly.
- Constitution digest is deploy-time `CONSTITUTION_SHA256` compared to a hashed
  `constitution.json` body. A mismatch halts before enqueue.

## Cost

Ten Sandbox buckets created and deleted per ten-cycle live run. Skip/halt does not create
a bucket (broker is paused). Audit OPEN/CLOSE objects remain in object lock. Lambda
invokes and Dynamo writes are negligible. No model. Effectively $0.

## Deviations from plan

1. **Wake stays DISABLED.** Tests invoke the runtime Lambda with an EventBridge-shaped
   payload. The rule is attached (`rootstock-runtime-wake`, `rate(4 hours)`) and is not
   enabled. That is the Phase 3 contract, not a skip.
2. **Criterion 5 live kill is reserved concurrency 0, not mapping-disable alone.** See
   design finding.
3. **Cursor is durable.** Live cycles continue from wherever the previous run left
   `next_cycle` (this close-out ended at 48), not from 1. That is correct for a persistent
   organism and noisy if you expect fixture-style isolation.
4. **Phase 2 live no longer assumes the broker role.** `assume_broker_role` was deleted
   after the live pass. Broker `sts:AssumeRole` remains, but only into
   `RootstockSandboxOperatorRole`.

## Design findings

### Event source mapping `Disabled` is not "broker killed"

Criterion 5 says killing the broker mid-flight must skip, then halt after lease expiry.
Setting the SQS event source mapping to `Disabled` and waiting for `State=Disabled` is not
enough:

- In-flight polls still complete.
- Standard SQS is at-least-once; a drain in the test can race a delivery the mapping
  already claimed.

Runs that only disabled the mapping saw skip succeed, then the next wake *enqueue* with
`expected_outcome_met=True` — the broker had closed the prior decision in the gap. The
live test now sets `ReservedConcurrentExecutions=0` on `rootstock-broker`, disables the
mapping, drains the queue, then injects an expired `PENDING` claim. `finally` drains
*before* restoring concurrency and re-enabling the mapping.

Unit tests already distinguished skip vs halt with `FrozenClock` and did not need this.
The finding is about what "kill the broker" means on AWS, not about VERIFY logic.

### Observation cannot be a Sandbox list

The runtime role has no Sandbox authority (criterion 4). Cycle *N+1* "observing" the
bucket from cycle *N* is a reconstruction from the closed decision's `actual_outcome` /
artifacts, not `s3:ListBuckets`. That is AR-2 working as specified, and it is why the
broker's AUDIT CLOSE / decision close is load-bearing for LEARN.

## Blocker encountered

Skip/halt live failed three times while the mapping was "Disabled" and the queue was
being drained. The failure mode was always the same: skip passed, halt saw a *closed*
prior and enqueued. Fixing the kill (throttle to zero) made the criterion pass on the
next run (31.60s isolated, then 143.04s full suite). Failed attempts left
`rootstock-sbx-cycle-*` buckets which were deleted before close-out. No cycle buckets
remain.

## Ready for Phase 4

Yes. All six Phase 3 exit criteria pass. Do not start Phase 4 until this file exists —
it does now. Wake stays disabled. `D1` (killing the runtime produces an external alert)
is Phase 4's job, not a leftover from this slice.
