# Phase 6 — Model insertion

> **Verdict: complete, with design findings, revised same day.** `ModelReasoner`
> implements the same `Reasoner` interface as the stub. Inference is Amazon Bedrock
> (GPT-5.6 Terra) via IAM; `rootstock/model-api-key` is gone. The live Lambda stays on
> `REASONER=stub`. `D1`–`D7` still pass. The swap was not perfectly boring: configuration,
> observation payload extraction, and decision-store persistence leaked outside the
> adapter. The HTTP client / second `urlopen` / Secrets Manager key were reversed. The
> propose/execute boundary did not. Do not enable the wake rule. Do not set
> `REASONER=model` until Terra is enabled in the Bedrock console.

## Commit / revision

```text
branch          main
base commit     7cbd96f  ("Record Phase 5 adversarial validation.")
working tree    Phase 6 (this record)
terraform       infra/v0, local state (not committed)
apply           2026-08-26T16:13Z  (0 added, 0 changed after output cleanup)
```

## Environment

```text
Python          3.12.3
uv              0.11.6
Terraform       1.9.8
AWS CLI         2.33.12
OS              Linux 7.0.0-30-generic
live model      2026-08-26T16:14Z  make v0-model-live  (1 passed in 14.85s)
live D1–D7      2026-08-26T16:16Z  pytest -m destructive … D1–D7  (7 passed in 69.81s)
```

SSO sessions for both `rootstock-core` and `rootstock-sandbox` were already valid.

## Tests run

```text
ruff check / format                 pass
mypy --strict                       pass (58 source files)
pytest -m 'not destructive and not live'   pass (113 passed, 17 deselected)
terraform fmt / infra/v0 validate   pass
make v0-model-live                  pass (1 passed)
D1–D7 live (Phase 5 suite, stub)    pass (7 passed, 3 deselected)
```

## AWS context resolved

```text
profile     rootstock-core
zone        core
account     111111111111

profile     rootstock-sandbox
zone        sandbox
account     022222222222
```

Wake rule `rootstock-runtime-wake` remains `DISABLED`. Runtime env `REASONER=stub`.
Secret `rootstock/model-api-key` exists; version is the placeholder `"not-configured"`.
Prompt object `prompts/v0.json` is in the grant bucket.

## Exit criteria

| # | Criterion | How | Result |
| --- | --- | --- | --- |
| 1 | Swap touched no file outside the reasoner adapter and its configuration | Diff vs Phase 5. Leaks listed below. Loop and broker protocol unchanged | recorded |
| 2 | `D1`–`D7` still pass unchanged | Live destructive controls, same bodies as Phase 5 | pass |
| 3 | The model cannot cause an invocation the stub could not have caused | Canned undeclared → no execute; out-of-scope → `DENIED`; source has no `assume_role` | pass |
| 4 | Provider cap verified by exceeding it deliberately in a test account | In-process `SpendCap` severs before the HTTP call. AWS Budgets refused in Core. No third-party provider account | adapter pass; provider finding |

## Observed results

- `ModelReasoner` + `FakeModelClient` produce the same happy-path bucket as `StubMode.NORMAL`.
  Rationale is prefixed `[model-generated] input_hash=…` and matches `observed_hash`.
- Placeholder secret `"not-configured"` cannot construct `HttpsModelClient`.
- HTTPS client POSTs only to the constructor URL; there is still no `http_request()` helper.
- Live runtime noop still uses the stub. The adapter is deployed and unwired.

### Criterion 1 — what leaked

| File | Why it changed | Protocol leak? |
| --- | --- | --- |
| `src/rootstock/runtime/model.py` | Adapter | no — the intended file |
| `src/rootstock/runtime/aws.py` | `reasoner_from_env()`; Dynamo now persists `rationale` / `alternatives_json` | no — config + storage mapper. Loop already wrote those fields |
| `src/rootstock/runtime/observe.py` | Extracted `observation_payload()` so model input hashes identically | no — serialization, not authority |
| `src/rootstock/runtime/heartbeat.py` | Document the second `urlopen` | no |
| `src/rootstock/runtime/__init__.py` | Export `ModelReasoner` | no |
| `tests/unit/test_heartbeat.py` | Allow `model.py` as a second `urlopen` site | no |
| `infra/v0/lambdas.tf` | `REASONER`, `MODEL_SECRET_ID`, `PROMPT_KEY` | configuration |
| `infra/v0/grant-objects.tf` + `grant-store/prompts/v0.json` | Versioned prompt artifact | configuration |
| `infra/v0/core-state.tf` | `ignore_changes` on secret version so a real key is not overwritten | configuration |
| `infra/v0/outputs.tf` | `model_secret_name`, `prompt_key` | configuration |

`src/rootstock/runtime/loop.py` and the broker were not modified.

## Cost

No live inference. The runtime remains on the stub. Cycle cost is unchanged from
Phase 5 (~$0.000036). Adapter `SpendCap` default is `max_usd_per_call` from the prompt
(`0.05`); it is not charged on the live path.

## Deviations from plan

1. **Live Lambda stays on the stub.** Phase 6 inserts the adapter and proves it is a
   drop-in. It does not flip `REASONER=model`. Sequence rule 3 still forbids unattended
   inference until a provider cap is verified.
2. **AWS Budgets cannot be created in Core.** Apply failed with
   `AccessDeniedException: Account 111111111111 is a linked account. To enable budgets
   for your account, ask the payer account to enable budgets first.` The `budget.tf`
   resource was removed. Adapter `SpendCap` is the cap that can be verified from this
   account.
3. **Second `urlopen` site.** Phase 4 required exactly one outbound HTTP call site.
   `HttpsModelClient` adds a second, same pattern: fixed HTTPS URL, no `http_request()`
   helper. AR-16 still holds.
4. **Criterion 1 failed as written, on purpose.** The plan said to stop and record.
   The leaks are listed above. They do not move authority into the reasoner.
5. **Wake stays DISABLED.**

## Design findings

### The propose/execute split survived; "one adapter file" did not

Wiring a second `Reasoner` required a configuration switch, a grant-store prompt, and
making the observation payload a named function so the model hashes what VERIFY already
hashed. The decision mapper had been dropping `rationale` and `alternatives` that the
loop already stored in memory. None of that is a broker or IAM change. If a later
reasoner needs to enqueue, assume a role, or skip schema, that *would* be the finding
this phase was watching for. It did not happen.

### AR-8 cannot be met from a member account today

AWS Budgets with enforcement actions is the layer AR-8 names. Core is a linked account;
the Management/payer account must enable budgets first. That is an operations item on
Management, which this repository is not allowed to target (AR-1). Application-level
`SpendCap` severs inference before `urlopen` and was exceeded deliberately in unit
tests. It is additional, not primary, exactly as AR-8 warns. Do not treat the adapter
cap as satisfying AR-8. Do not run unattended inference until either the payer enables
Budgets with a hard cap, or a real model-provider cap is configured and exceeded in a
test account.

**Same day, after this record:** the payer enabled member budgets. Core
`rootstock-core-monthly` and Sandbox `rootstock-sandbox-monthly` ($10, automatic
IAM-attach of Deny-all to the organism roles) now exist and are in `infra/v0/budgets.tf`.
That is the AWS-spend layer. A model-provider cap is still required before
`REASONER=model`. Management org budget + SCP `rootstock-budget-halt` is hand-operated
and not in this repository.

### A placeholder secret is the live key, and that is correct

Terraform seeds `"not-configured"` and ignores later `secret_string` changes so a real
key set out of band is not overwritten on apply. `HttpsModelClient` refuses the
placeholder. There is no path from the deployed Lambda to a model API until a human
writes a real secret *and* sets `REASONER=model`. Those are two deliberate acts, not
one.

## Blocker encountered

First `make v0-apply` for this phase created the prompt object and Lambda env, then
failed on AWS Budgets. Re-apply after deleting `budget.tf` converged (output
`inference_budget_name` dropped from state). No infrastructure other than that output
changed.

## Ready for Phase 7

Yes, on the stub, with the wake rule still `DISABLED`. Phase 7's 100 unattended cycles
are a wake-rule decision, not a model-flip decision. Do not set `REASONER=model`. Do
not put a real API key in terraform. Raise AR-8 against `docs/design/` when Management
work is scheduled; do not quietly drop it.

---

## Same-day revision — Bedrock, not an external key

The earlier record above is what shipped first (`HttpsModelClient` + placeholder
`rootstock/model-api-key`). The same day, the model provider decision was revised:

```text
rootstock-runtime-role
        │ IAM  bedrock:InvokeModel  (Terra only)
        ▼
Amazon Bedrock
        │
        ▼
GPT-5.6 Terra   (us.openai.gpt-5.6-terra)
```

No provider secret. No `MODEL_SECRET_ID`. No second `urlopen`. Heartbeat is again the
only outbound HTTP call site. Bedrock usage bills in Core and is therefore inside
`rootstock-core-monthly`.

The broker still cannot invoke models. The runtime still cannot assume Sandbox roles.
`REASONER` remains `stub` until Terra is enabled in the Bedrock console — that is a
human act, not an apply.

Adapter `SpendCap` still severs before `converse`. IAM pins the geo CRIS id; the prompt
cannot escalate.

```text
apply           2026-08-26T17:40Z  0 added, 5 changed, 2 destroyed (secret gone)
IAM negatives   pass (broker InvokeModel implicitDeny; runtime non-Terra implicitDeny)
make v0-model-live  pass (prompt present, BEDROCK_MODEL_ID=us.openai.gpt-5.6-terra,
                    MODEL_SECRET_ID absent, secret scheduled for deletion)
wake            DISABLED
REASONER        stub
```

