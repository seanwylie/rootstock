# Rootstock v0 — Implementation Plan

> **Status: Active.** Authored 2026-08-26. First implementation slice of rung **0.0**.
>
> Conforms to `docs/design/00-system-boundaries.md`, `01-rootstock-v0.md`,
> `02-capability-model.md`, and `03-runtime-and-broker.md`. This document says *how*; those
> say *what must be true*. If a phase here cannot satisfy an `AR-*` requirement, that is a
> design finding to be raised — never a requirement to be quietly relaxed.

## Objective

> An autonomous process running in Core wakes, inspects deterministic state, makes one
> bounded decision, invokes one capability in Sandbox, records the result, updates
> institutional memory, and goes dormant — without human execution.

## The organising decision: build the organism before the mind

**The model is connected last, in Phase 6.** Everything before it runs against a
`StubReasoner` that returns a deterministic, hardcoded proposal.

This is an experimental control, not a shortcut. The loop, the gates, the audit chain and the
replay semantics are all mechanical properties; a model in the middle of them adds
nondeterminism to every failure and turns "why did that break" into a debate about what the
model did. If the pipeline cannot move a hardcoded proposal from EventBridge through to a
tagged bucket in Sandbox, a model contributes nothing useful to debugging it.

The other reason is diagnostic. Swapping `StubReasoner` for `ModelReasoner` in Phase 6 should
be **boring** — one adapter, no other changes. If it is not boring, the boundary between
proposing and executing was drawn in the wrong place, and that is worth discovering in an
afternoon rather than after the architecture has set.

```text
EventBridge → runtime → VERIFY → OBSERVE → StubReasoner → CapabilityRequest
                                                                │
                                                              SQS
                                                                ▼
   next wake observes reality ◀── result ◀── one harmless side effect
                                              ▲
   broker ← schema ← claim ← policy ← audit-open ← scoped Sandbox session
```

## Decisions this plan needs that design does not specify

| Decision | Lean | Settle by |
| --- | --- | --- |
| Language | Python 3.12 — Lambda-native, matches Argus, good AWS SDK ergonomics | Phase 0 |
| IaC | Terraform — state is inspectable and destroy/recreate is cheap for a test env | Phase 0 |
| Test framework | pytest, plus a separate destructive-test runner that talks to real AWS | Phase 0 |
| Heartbeat provider | Any hosted dead-man's-switch; must alert to a channel Rootstock cannot reach | Phase 4 |
| Model provider | Amazon Bedrock + GPT-5.6 Terra; IAM, not a key. Live Lambda stays stub | Phase 6 |
| Repo layout | `infra/`, `runtime/`, `broker/`, `shared/`, `tests/` | Phase 0 |

Everything above is a plan-level choice and can change without touching `docs/design/`.

## Phase evidence

Every phase closes by writing a record. Not a document to be designed — a fixed convention,
so the trail exists without anyone deciding to create it.

```text
docs/plans/v0/evidence/
    phase-0.md
    phase-1.md
    ...
```

Each record contains:

```text
commit / terraform revision
environment
tests run
destructive tests run
observed results
cost observations
deviations from plan
design findings
exit criteria verdict
```

**A phase is not complete until its record exists.** This is the difference between a
codebase that satisfies its architecture and one that can *demonstrate* it did — the final
code state shows what is true now, and says nothing about whether AR-4 was ever actually
verified or merely assumed.

Two fields carry most of the value. `deviations from plan` is where this document gets
corrected by reality. `design findings` is the escalation path from sequencing rule 5: when
an `AR-*` requirement cannot be met as written, it is recorded here and raised against
`docs/design/`, never dropped from a checklist.

---

## Phase 0 — Test harness

Build the thing that tells us whether anything works, before building anything.

- [x] Repo skeleton, dependency management, formatter and linter
- [x] Terraform workspace for a disposable test environment, targeting Sandbox
- [x] Fixture library: construct a `CapabilityRequest` and submit it without a runtime
- [x] Destructive-test runner — a harness that can break things deliberately and assert on
      the failure mode, not just on success
- [x] `StubReasoner`: deterministic, configurable, zero model dependency
- [x] Teardown that provably leaves nothing behind

**Exit criteria**

1. `terraform apply` and `terraform destroy` both run clean, twice in a row.
2. A fixture can submit a request to a component that does not exist yet and fail with a
   clear error rather than a stack trace.
3. Teardown verified by listing Sandbox and finding zero `rootstock-sbx-*` resources.

*Why first: the destructive tests are the point of v0. A harness retrofitted after the code
tends to test what the code does rather than what the architecture requires.*

---

## Phase 1 — Substrate

All infrastructure, no logic.

- [x] DynamoDB: `rootstock-memory`, `rootstock-decisions`, `rootstock-claims`,
      `rootstock-approvals` (F-1)
- [x] S3: grant store bucket, audit bucket with object lock
- [x] SQS: `rootstock-capability-requests` + dead-letter queue
- [x] EventBridge wake rule, disabled initially
- [x] Core IAM: `rootstock-runtime-role`, `rootstock-broker-role`, exactly as specified in
      `03-runtime-and-broker.md`
- [x] Sandbox IAM: `RootstockSandboxOperatorRole` with `ExternalId` and `aws:PrincipalOrgID`.
      `aws:RequestTag` conditions were applied in Phase 1 and **removed in Phase 2** — S3
      does not populate them (see `docs/plans/v0/evidence/phase-2.md`)
- [x] Grant store seeded with the constitution, the six 0.0 capability declarations, and
      policy rules

**Exit criteria**

1. **IAM negative assertions pass.** `rootstock-runtime-role` has no `sts:AssumeRole` in its
      effective policy — asserted by IAM policy simulation, not by reading the Terraform.
2. `rootstock-broker-role` cannot read the model secret and cannot delete from the audit
      bucket.
3. `rootstock-runtime-role` cannot write to the grant store.
4. Neither role can assume anything in Management.
5. Object lock verified by attempting a delete on the audit bucket and failing.

*The negative assertions are the deliverable. Standing up tables is trivial; proving the
absence of authority is the part that makes AR-2, AR-4, AR-6 and AR-12 real.*

---

## Phase 2 — Broker vertical slice

One capability, end to end, driven by fixtures. No runtime yet.

- [x] `CapabilityRequest` schema, versioned; ingress validation (AR-16)
- [x] Canonical id derivation — `sha256(idempotency_key ‖ capability ‖ target ‖ canonical_json(parameters))`
- [x] Claim table with lease, conditional write, and the `PENDING`/`EXECUTED`/`FAILED`/`UNKNOWN` state machine (AR-15)
- [x] Policy evaluator: ordered checks, first DENY wins, returns the deciding rule
- [x] **AUDIT OPEN — durable write required before execution** (AR-4)
- [x] STS assume with per-invocation session policy; session name = `canonical_id` (AR-7)
- [x] Executor for `sandbox.s3.create_bucket`, prefix applied server-side from a suffix
- [x] AUDIT CLOSE; `UNKNOWN` on failure, never `FAILURE`
- [x] `CapabilityResult` persisted; decision record closed

**Exit criteria**

1. A fixture request creates a correctly tagged bucket in Sandbox.
2. **Replay:** the identical request submitted twice produces exactly one bucket, one audit
      chain, and a second result of `DUPLICATE`.
3. **Undeclared capability id** is rejected at ingress, before policy evaluation runs.
4. **Out-of-scope parameters** are denied, and the response names the deciding rule.
5. **AUDIT OPEN failure blocks execution** — no bucket is created.
6. **AUDIT CLOSE failure after a successful call** yields `UNKNOWN`, leaves the claim
      non-terminal, and raises an incident.
7. Reconciliation resolves that `UNKNOWN` by querying S3 and closing the record correctly.
8. Effective session permissions are strictly narrower than the role's ceiling.

*Do not start Phase 3 until **this phase's exit criteria** 2 (replay) and 6 (AUDIT CLOSE →
`UNKNOWN`) both pass. Those are the same gate as sequencing rule 1, and they are far cheaper
to fix before a runtime is calling into the broker. They are not a requirement to finish
Phase 6 (model insertion) first — the model is connected last.*

---

## Phase 3 — Runtime vertical slice

- [x] VERIFY: constitution digest, grant store readable, prior-cycle state
- [x] Prior-cycle handling — the four outcomes: closed, awaiting approval, lease valid
      (skip), lease expired (halt)
- [x] OBSERVE: assemble the deterministic payload; no free text, no external content
- [x] LEARN: append claims derived from the previous cycle's actual outcome
- [x] `StubReasoner` returning one proposal
- [x] DECIDE: open the decision record with a checkable `expected_outcome`; enqueue
- [x] Dormant exit holding no state

**Exit criteria**

1. Ten consecutive scheduled cycles complete with no human execution.
2. Cycle *N+1* observes the bucket created in cycle *N* and records that its
      `expected_outcome` was met.
3. A cycle proposing nothing still writes a decision record.
4. The runtime is shown to have no way to invoke a capability directly (`D3`).
5. Killing the broker mid-flight causes the next wake to skip, and the wake after an expired
      lease to halt — the two are distinguished correctly.
6. Decision records show two authors: opened by runtime, closed by broker.

---

## Phase 4 — Liveness

- [x] `heartbeat.ping()` — no arguments, fixed configured endpoint
- [x] **No `http_request()` helper anywhere in the codebase** (AR-16)
- [x] External dead-man's-switch configured, alerting outside Rootstock's reach
- [x] Expired-lease detection and alert
- [x] DLQ alarm

**Exit criteria**

1. Killing the runtime produces an external alert within the configured window (`D1`).
2. Rootstock cannot silence, extend, or delete the monitor — verified by attempting it.
3. A poison message reaches the DLQ and alarms rather than retrying indefinitely.
4. Code search for outbound HTTP finds exactly one call site.

---

## Phase 5 — Adversarial validation

The phase that decides whether v0 is real. Every destructive test from
`docs/design/01-rootstock-v0.md`, run against the assembled system with the stub.

- [x] `D1` kill runtime → external alert fires
- [x] `D2` alter constitution digest → VERIFY halts
- [x] `D3` attempt capability from runtime → fails, no `sts:AssumeRole` to attempt with
- [x] `D4` replay identical request → one side effect, second is `DUPLICATE`
- [x] `D5` undeclared capability id → rejected at ingress
- [x] `D6` out-of-scope parameters → DENY naming the rule
- [x] `D7` revoke broker audit write → AUDIT OPEN fails, no execution occurs
- [x] `D8` fail AUDIT CLOSE after a successful call → `UNKNOWN`, not `FAILURE`
- [x] CloudTrail reconciliation: every Sandbox mutation joins to a decision record by
      session name
- [x] Cost per cycle measured, with estimate-to-actual variance recorded

**Exit criteria**

1. All eight destructive tests pass, and each is automated and repeatable.
2. Zero Sandbox mutations exist without a corresponding decision record.
3. Cost per cycle is known within a stable range.

*`D7` and `D8` are the likely failures, and they fail in opposite directions — one by
auditing too late, the other by overcorrecting and lying about a side effect that already
happened.*

---

## Phase 6 — Model insertion

If this phase is interesting, something is wrong.

- [x] Amazon Bedrock via IAM (`bedrock:InvokeModel` on GPT-5.6 Terra only). No
      `rootstock/model-api-key`. Runtime has an identity, not a password (AR-12).
- [x] Prompt as a versioned artifact in the grant store — configuration, not code
- [x] `ModelReasoner` implementing the same interface as `StubReasoner`
- [x] Model input and output recorded, marked unambiguously as model-generated
- [x] Adapter `SpendCap` configured and exceeded in unit tests **before first unattended
      inference**. Member-account AWS Budgets with automatic IAM-attach actions now exist
      in Core and Sandbox (`infra/v0/budgets.tf`) and also cap Bedrock usage. Org SCP
      backstop is hand-built in Management and not in this repo. Do not set
      `REASONER=model` until Terra is enabled in Bedrock (see
      `docs/plans/v0/evidence/phase-6.md`).

**Exit criteria**

1. `StubReasoner → ModelReasoner` touched no file outside the reasoner adapter and its
      configuration. **If it did, stop and record what leaked** — that is a design finding
      about the propose/execute boundary and belongs in `docs/design/`.
      Recorded: configuration, observation payload, decision-store persistence. The
      HTTP `HttpsModelClient` / second `urlopen` / Secrets Manager key were reversed the
      same day in favour of Bedrock IAM. Loop and broker unchanged. Live `REASONER`
      remains `stub`.
2. All of `D1`–`D7` still pass unchanged.
3. The model cannot cause an invocation the stub could not have caused.
4. Provider cap verified by exceeding it deliberately in a test account.
      Adapter cap: pass. AWS member budgets: in place (cap Bedrock as AWS spend). Live
      `REASONER` remains `stub` until Terra is enabled in the Bedrock console.

---

## Phase 7 — Qualification

Split after the stub run. **0.0 closes only after 7b.**

### Phase 7a — Stub qualification

- [x] 100 consecutive autonomous cycles
- [x] Zero unaudited actions
- [x] Cost per cycle stable and recorded (~$0.000043 mechanical floor)
- [x] Memory contains claims a later cycle demonstrably read
- [x] the operator executed nothing for the duration

**Exit criteria (organism):** the six operational success criteria and `D1`–`D8` on the
stub. See `docs/plans/v0/evidence/phase-7.md`.

**Verdict: PASS.** Wake is now `DISABLED`. Live `REASONER` remains `stub`.

### Phase 7b — Model qualification

- [ ] 10–20 supervised Terra cycles (not another 100-cycle marathon)
- [ ] Structured `noop` is a real choice, not a broker capability
- [x] Memory schema is the designed claim record (deployed; Terra has not written one)
- [x] `D1`–`D8` still hold (stub, after 7b deploy)
- [ ] Cycle cost = mechanical floor + Terra inference

**Verdict: BLOCKED** (2026-08-28). First supervised invoke failed: Core Bedrock
account verification. Wake stayed `DISABLED`; `REASONER` restored to `stub`.
See `docs/plans/v0/evidence/phase-7b.md`. Retry `make v0-qualify-7b` after AWS
verifies the account. Do not enable EventBridge to wait.

Do not start 0.1 research until 7b passes. The next experiment is Terra, not an external
world.

---

## Sequencing rules

Ignoring these turns a staged build back into "Terraform everything, write everything, test
everything":

1. **No runtime before the broker survives replay and audit failure** under fixtures
   (Phase 2 exit criteria 2 and 6 — not "wait for Phase 6").
2. **No model before `D1`–`D7` pass with the stub** (Phase 5 before Phase 6).
3. **No unattended inference before the provider spend cap is verified.**
4. **No phase starts until the previous phase's exit criteria are met and recorded.**
5. **Any `AR-*` requirement that cannot be met is escalated as a design finding**, never
   dropped from a checklist.
6. **Do not introduce a real-world capability before the rung that needs it.** A refund cap,
   a public domain, or venture-independence machinery at 0.0 is unused surface, not safety
   (Q5, Q6).

## Deliberately out of scope

Belongs to later rungs, listed so nobody adds it helpfully: web research, model-generated
code, deployment of anything reachable, DNS, email, any spending beyond inference, ventures,
multiple capability invocations per cycle, and approval notification transport beyond the operator
reading a queue.

## Risks

| Risk | Mitigation |
| --- | --- |
| `D7` fails and the fix is invasive | Two-phase audit is specified before Phase 2 starts, not discovered during it |
| Model insertion is not boring | Treated as a design finding, not patched around |
| Stub is too well-behaved to be a real test | Give it modes that propose denied, malformed, and out-of-scope requests |
| Lambda cold starts distort cost measurement | Measure across enough cycles to separate cold from warm |
| Scheduled cycles accumulate slowly | Wake interval configurable; shorten it in test, not in qualification |
| 100 cycles pass while learning nothing | Criterion 5 requires memory a later cycle actually read |
