# Phase 7 — Qualification

> **Verdict: Phase 7a PASS; Phase 7b PENDING.** 100 consecutive EventBridge-driven cycles
> closed on the stub (cycles 73–172). The operator did not invoke the runtime for those cycles.
> Every cycle has a closed decision record and an `EXECUTED` claim. CloudTrail Event
> history in the window had zero unmatched operator `CreateBucket` sessions. Cost is
> ~$0.000043 / cycle. Memory `learned` claims were read by later cycles via
> `memory.recent()`. `D1`–`D8` still pass. Live `REASONER` remains `stub`. After the
> window, wake was restored `ENABLED` at `rate(4 hours)`, then **DISABLED** so the stub
> would not keep creating buckets. Rung 0.0 is not closed.

## Commit / revision

```text
branch          main
base commit     0f2634e  ("Correct Bedrock access: OpenAI models have no enable button.")
working tree    Phase 7 (this record)
terraform       infra/v0, local state (not committed)
wake            ENABLED  rate(4 hours)  after a 1-minute accumulation window
REASONER        stub
```

Raw run: [`phase-7-run.json`](phase-7-run.json).

## Environment

```text
Python          3.12.3
uv              0.11.6
Terraform       1.9.8
AWS CLI         2.33.12
OS              Linux 7.0.0-30-generic
qualify start   2026-08-26T18:45:01Z
qualify end     2026-08-26T20:25:53Z
elapsed         6047s (~101 min) for 100 cycles
D1–D8           2026-08-26T20:32Z  make v0-destructive-live  (10 passed in 304.50s)
```

SSO sessions for both `rootstock-core` and `rootstock-sandbox` were already valid.

## Tests run

```text
ruff / mypy / unit                  pass (before enable; 114 passed)
make v0-qualify                     pass (100 closed cycles, 0 claim gaps)
make v0-destructive-live            pass (10 passed; D1–D8 + CloudTrail + cost tests)
```

## Destructive tests run

All eight, after the 100-cycle window, with wake temporarily `DISABLED` so D1 would not
race the scheduler. Restore left wake `ENABLED` at the design cadence.

## AWS context resolved

```text
profile     rootstock-core
zone        core
account     111111111111

profile     rootstock-sandbox
zone        sandbox
account     022222222222
```

## Exit criteria

| # | Criterion | How | Result |
| --- | --- | --- | --- |
| 1 | 100 consecutive autonomous cycles | EventBridge `rootstock-runtime-wake`; observer did not invoke Lambda | pass (73–172) |
| 2 | Every cycle produced a decision record | Dynamo `rootstock-decisions` state=`closed`, `opened_by=runtime`, `closed_by=broker` | pass |
| 3 | Zero unaudited capability invocations | 100/100 claims `EXECUTED`; CloudTrail operator `CreateBucket` orphans = [] (99 events joined after 90s ingest) | pass |
| 4 | Cost per cycle known and stable | CloudWatch `AWS/Lambda` Duration over the window | pass (~$0.000043) |
| 5 | Memory contains claims a later cycle read | Cycle 122 `learned` row; cycle 123 persisted `observed_hash` (OBSERVE always calls `memory.recent()`) | pass |
| 6 | the operator executed nothing for the duration | No `lambda:InvokeFunction` of the runtime by the observer; scheduler was EventBridge | pass |
| — | `D1`–`D8` still hold | `make v0-destructive-live` after the window | pass |

## Observed results

- Stub `NORMAL` proposed `sandbox.s3.create_bucket` every cycle. Sandbox now holds
  `rootstock-sbx-cycle-73` … `rootstock-sbx-cycle-172` (plus any cycles that fired
  after the observer returned and before wake was paused).
- Heartbeats landed; silence window was 300s during the 1-minute schedule, then 28800s
  (8h, two missed 4-hour wakes) at the design cadence.
- `expected_outcome_met` on the mid-window learned claim was `true`.

## Cost

```text
estimated_cost     $0.00  (stub)
runtime Duration   5519 ms avg  (101 samples, 256 MB)
broker Duration    4776 ms avg  (101 samples, 256 MB)
actual             $0.00004330 / cycle
variance           $0.00004330
stable range       still well under $0.0001 / cycle; no model
```

One extra runtime/broker sample versus 100 cycles is the EventBridge/Lambda metric
bucket; it does not change the range.

## Deviations from plan

1. **Schedule was shortened for accumulation.** The plan said to shorten the interval in
   test, not in qualification. `rate(4 hours)` × 100 = ~16.7 days. Qualification used
   `rate(1 minute)` so EventBridge was still the scheduler and the operator still executed
   nothing. After the window, cadence is `rate(4 hours)` `ENABLED`.
2. **Skipped-cycle records were not exercised.** Design criterion 2 includes skipped
   cycles. The skip path still returns without writing a decision record. No skip
   occurred (1 minute > cycle time), so the 100-cycle window did not prove that clause.
3. **The 100 cycles used the stub, not Terra.** Sequence rule 3 and the Phase 6 record
   still forbid unattended inference. The organism is qualified; the mind is not live.
4. **CloudTrail is still Event history**, not an organization trail. 99 of 100
   `CreateBucket` events had joined after 90s; the 100th was claim-backed and not an
   orphan. Re-check of decisions vs claims was 100/100.

## Design findings

### The organism is real on the stub

Unattended wake, one bounded Sandbox mutation per cycle, audit-open/execute/audit-close,
heartbeat, and memory read-back all held for 100 consecutive cycles. That is rung 0.0
as specified, with the model still unwired.

### Skip records do not exist

`CycleRunner` skip returns `action=skipped` and does not `decisions.open`. Design
criterion 2 asked for a record including skipped cycles. Raise against
`docs/design/01-rootstock-v0.md` rather than silently treating skip as "no cycle".

Resolved after 7a: semantics B (a skipped wake is not a cycle). Wake records exist;
criterion 2 was corrected.

### Memory is a learned log, not the claim schema

Design asked for applicability, expiry, confidence, `derived_from`. What later cycles
actually read is `{kind, actual_outcome, expected_outcome_met, canonical_id}`. That is
enough for 0.0 self-observation. It is not the institutional-memory schema.

Resolved after 7a: LEARN now writes the designed claim schema. Existing stub-run rows
remain the short form.

### The stub will fill Sandbox forever

100 tagged buckets in one sitting is the "identical bucket" failure mode the design
flagged. Inventory and `expected_outcome_met` work; they do not stop the next create.
Do-nothing detection remains an open item. Flipping `REASONER=model` is the first
chance the loop has to choose `noop`.

### Cost example in the design was high by two orders of magnitude

The illustrative claim "cycle cost averages $0.004" is ~100× this stub. Keep that
figure out of memory until a live model run exists.

## Blocker encountered

None. Wake enable was a terraform state change (`var.wake_state`).

## Ready for 0.1

Not until Phase 7b (Terra) passes. Rung 0.0 is **not** closed on the stub. Do not treat
Terra as live. After the 100-cycle window the 4-hour stub wake was re-enabled; that was
a mistake to leave running. The stub wake is now `DISABLED`.

## Bookkeeping after 7a (2026-08-26)

```text
Phase 0   Harness                    PASS
Phase 1   Substrate                  PASS
Phase 2   Broker                     PASS
Phase 3   Runtime                    PASS
Phase 4   Liveness                   PASS
Phase 5   D1–D8                      PASS
Phase 6   Model integration          PASS
Phase 7a  Stub qualification         PASS
Phase 7b  Model qualification        PENDING

Rootstock 0.0 substrate/organism qualification passed.
Model-driven autonomy is not yet qualified.
Rootstock 0.0 = CLOSED only after 7b.
```

Three decisions taken before carrying 0.0 forward:

1. **Disable the stub wake.** The scheduler is already qualified. Further
   `rate(4 hours)` stub buckets are junk. Leave `wake=DISABLED`, `REASONER=stub`
   until the first Terra cycles.
2. **A skipped wake is not a cycle (semantics B).** Write a wake record; do not
   write a decision; do not increment the cursor. Criterion 2 in
   `docs/design/01-rootstock-v0.md` was updated. Do not carry the old sentence
   into 0.1.
3. **Next experiment is Terra, not 0.1 research.** 10–20 supervised Terra cycles
   with a real `action=noop` vocabulary (not a broker capability) and the designed
   memory claim schema. Then `D1`–`D8`. Then 0.0 can close.

Mechanical floor measured in this phase: **~$0.000043 / cycle**. Essentially all
economically meaningful 0.0 cost will come from inference.
