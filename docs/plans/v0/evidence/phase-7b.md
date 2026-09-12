# Phase 7b — Model qualification

> **Verdict: blocked.** Supervised Terra was attempted with EventBridge **DISABLED**.
> The first `Converse` call failed: Core account `111111111111` is still in AWS
> account verification. `REASONER` was restored to `stub`. Wake stayed `DISABLED`.
> Zero Terra cycles completed. Rung 0.0 is not closed.

Raw run: [`phase-7b-run.json`](phase-7b-run.json).

## Commit / revision

```text
branch          main
base            9600893  (7a follow-up: skip/noop/schema, wake default DISABLED)
terraform       infra/v0, local state (not committed)
wake            DISABLED  throughout
REASONER        stub before, model during the failed invoke, stub after restore
runtime timeout 120s
```

## Environment

```text
Python          3.12.3
attempt         2026-08-28T20:13Z  make v0-qualify-7b
blocker         Bedrock AccessDeniedException — account being verified
restore         REASONER=stub  wake=DISABLED  confirmed via GetFunctionConfiguration
cursor          next_cycle=220
```

SSO sessions for `rootstock-core` and `rootstock-sandbox` were valid.

## Cost controls that held

7b is **not** an EventBridge run. The script:

1. Refuses to start if `rootstock-runtime-wake` is `ENABLED`.
2. Flips only the Lambda env `REASONER=model`.
3. Restores `REASONER=stub` in `finally`.
4. Terraform defaults are `wake=DISABLED` and `reasoner=stub`, and
   `wake ENABLED` + `reasoner=model` cannot be applied together.

That last constraint is the structural answer to leaving the loop running. The
forgotten 4-hour **stub** wake after 7a produced extra Sandbox buckets; the same
mistake with Terra would have been inference spend, not $0.000043/cycle junk.

## Forgotten stub wake (the costing lesson)

After 7a, wake was restored `ENABLED` at `rate(4 hours)` and left on until
2026-08-28 apply. Snapshot before the Terra attempt:

```text
sandbox cycle buckets     141
7a qualified through      172
extra buckets after 172   41
                          173–201, 208–219
cursor                    220
mechanical extra          ~41 × $0.000043 ≈ $0.0018
```

Cheap on the stub. The damage is Sandbox clutter and a cursor that no longer
matches the 100-cycle window. If Terra had been live on that schedule, 41
unattended inference calls would have billed in Core inside
`rootstock-core-monthly`.

## Tests run

```text
make check                  pass (118 unit)
terraform apply             runtime timeout 120s; REASONER var default stub
make v0-qualify-7b          blocked on Bedrock verification; restore succeeded
make v0-destructive-live    pass (10 passed in 199.75s) after restore; wake still DISABLED
```

`D1`–`D8` still hold on the stub after the 7b deploy. They must be re-run again
once Terra actually completes cycles.

## Exit criteria

| # | Criterion | Result |
| --- | --- | --- |
| 1 | 10–20 supervised Terra cycles | blocked — 0 cycles |
| 2 | Structured `noop` is a real choice | not exercised live |
| 3 | Memory schema is the designed claim record | deployed; not exercised by Terra |
| 4 | `D1`–`D8` still hold | pass on stub after this deploy; not yet re-run with Terra |
| 5 | Cycle cost = mechanical floor + Terra | not measured — no successful `Converse` |

## Design findings

### Account verification is a 7b gate, not a prompt problem

IAM already pins `us.openai.gpt-5.6-terra`. The failure is AWS refusing
`Converse` until Core finishes account verification ("normally takes less than
2 hours"; write `aws-verification@amazon.com` if it lasts longer). Do not flip
`REASONER=model` again until a single supervised invoke succeeds.

### Unattended model is now hard to apply by accident

Terraform precondition forbids `wake=ENABLED` and `reasoner=model` together.
The 7b Makefile target refuses an enabled wake. The live default remains stub.

## Blocker encountered

First 7b invoke (2026-08-28T20:13Z): Bedrock *Your account is currently being verified.*

Operator `Converse` retry from Core SSO the same afternoon:

```text
aws bedrock-runtime converse --region us-east-1 --model-id us.openai.gpt-5.6-terra
AccessDeniedException: openai.gpt-5.6-terra is not available for this account
```

`list-inference-profiles` shows `us.openai.gpt-5.6-terra` **ACTIVE**. Applied quota
`L-99936FBF` (Terra US geo CRIS TPM) is **0**; default is **20,000,000**. A quota
increase request is rejected because it must exceed the default. Same 0 on Grok
`L-0F2ECB41`. This is entitlement, not IAM.

Support case (Account / Account Activation, Bedrock Allowlisting), opened from Core:

```text
Case ID    redacted
Opened     2026-08-28T20:43:08Z
Status     Unassigned
Opened by  ops+core@example.com
```

Retry `make v0-qualify-7b` only after `Converse` to `us.openai.gpt-5.6-terra`
succeeds. Do not enable EventBridge to wait.

## Ready for 0.1

No. 7b is not PASS. Wake stays `DISABLED`. `REASONER` stays `stub`.
