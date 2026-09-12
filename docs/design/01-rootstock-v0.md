# 01 — Rootstock v0

> **Status: Decided.** This document is normative. It specifies rung **0.0** of the version
> ladder in `docs/brainstorm/16-bootstrapping-rootstock.md`.

## The milestone

> **An autonomous process running in Core can wake, inspect deterministic state, make one
> bounded decision, invoke one capability in Sandbox, record the result, update institutional
> memory, and go dormant again — without human execution.**

That is the whole of v0. It proves the fundamental organism before we give it commerce.

## What v0 is not

Stated first, because the temptation to add capability here is strong and every addition
makes failure harder to interpret.

- **No money.** No treasury, no payment provider, no spending capability. Inference is the
  only cost, capped at the provider.
- **No domain registration.** No DNS, no public presence.
- **No emailing strangers.** No outbound communication of any kind. The only observer is
  the operator, reading records.
- **No autonomous venture creation.** No ventures exist, and `venture.*` capabilities are
  not declared.
- **No deployment.** Nothing Rootstock produces is reachable from the internet.
- **No web research.** That is rung 0.1. v0 does not read the outside world at all, which
  means the entire prompt-injection surface is absent by construction — a considerable
  simplification for the first working loop.

Six capabilities exist (`02`). Everything else is not merely denied but undeclared.

## The loop

The loop spans two processes. The runtime predicts and sleeps; the broker acts; the *next*
cycle confronts what actually happened.

```text
  rootstock-runtime                        rootstock-broker
  ─────────────────                        ────────────────
        ┌──────────────────────────┐
        ▼                          │
   ┌─────────┐                     │
   │  WAKE   │ scheduled           │
   └────┬────┘                     │
        ▼                          │
   ┌─────────┐                     │
   │ VERIFY  │ constitution hash,  │
   │         │ grant store,        │
   │         │ prior cycle closed  │
   └────┬────┘ ─ fails ─▶ HALT     │
        ▼                          │
   ┌─────────┐                     │
   │ OBSERVE │ deterministic state │
   │         │ incl. last result   │
   └────┬────┘                     │
        ▼                          │
   ┌─────────┐                     │
   │ LEARN   │ claims from the     │
   │         │ previous outcome    │
   └────┬────┘                     │
        ▼                          │
   ┌─────────┐                     │
   │ REASON  │ model proposes      │
   │         │ ONE action          │
   └────┬────┘                     │
        ▼                          │
   ┌─────────┐                     │
   │ DECIDE  │ open decision       │
   │         │ record; enqueue     │
   └────┬────┘ CapabilityRequest   │
        │                          │        ┌──────────┐
        ├───────── SQS ─────────────────────▶ INGRESS  │ schema  (AR-16)
        │                          │        └────┬─────┘
        ▼                          │             ▼
   ┌─────────┐                     │        ┌──────────┐
   │ DORMANT │ heartbeat, exit,    │        │  CLAIM   │ dedupe  (AR-15)
   │         │ hold no state       │        └────┬─────┘
   └────┬────┘                     │             ▼
        │                          │        ┌──────────┐
        └──────────────────────────┘        │   GATE   │ policy  (AR-3)
                                            └────┬─────┘
                                                 ▼
                                            ┌──────────┐
                                            │  AUDIT   │ pre-exec (AR-4)
                                            └────┬─────┘
                                                 ▼
                                            ┌──────────┐
                                            │ EXECUTE  │ ≤ 1 capability
                                            └────┬─────┘
                                                 ▼
                                            ┌──────────┐
                                            │  CLOSE   │ outcome, cost,
                                            └──────────┘ variance
```

The runtime never waits. It records what it expects to happen, hands the request to a
durable boundary, and exits. The result is waiting for it at the next `OBSERVE`.

Full protocol, identity graph, and replay mechanics in `03-runtime-and-broker.md`.

### Properties of the loop

**Exactly one capability invocation per cycle.** `[SETTLED for v0]` This is the single most
important constraint. It bounds cost per wake to something knowable, makes every cycle
trivially auditable, eliminates partial-completion states, and turns "what did it do?" into
a question with a one-line answer. Multi-action cycles arrive at 0.2 when there is something
worth building.

A cycle that decides to do nothing is a valid and healthy cycle. It still produces a
decision record.

**Dormant means dormant.** No process, no held state, no open connections. All continuity
lives in durable storage. This is not an optimization — it forces every piece of state to be
externalized and inspectable, and it makes the runtime restartable from any point.

**Fail closed at VERIFY.** If the constitution hash does not match or the grant store is
unreadable, the organism halts and alerts rather than proceeding. A Rootstock that cannot
verify its own constraints must not act.

The prior cycle's state needs three outcomes rather than two, because asynchronous execution
makes "not closed yet" a normal condition:

| Prior cycle | Action |
| --- | --- |
| Closed | Proceed normally (start a cycle) |
| Open, awaiting approval | Proceed. A parked request is a known state, not a stall |
| Open, broker lease still valid | Skip this wake. Write a **wake record**, not a decision. Re-sleep |
| Open, broker lease expired | **Halt and alert.** Record a halted cycle as an incident |

The distinction between the last two is the useful one. Skipping is normal impatience — the
scheduler fired while work was legitimately in progress. An expired lease means something
claimed a request and never finished it, which is precisely the condition that must never be
resolved by guessing.

A skipped wake is **not a cycle**. Vocabulary:

```text
Wake
├── HALT          VERIFY failed, or prior lease expired
├── SKIP          prior broker lease still valid — no cycle
└── START CYCLE   OBSERVE → LEARN → REASON → DECIDE → decision record
```

- **wake record** — every EventBridge invocation (`halt` / `skip` / `cycle`)
- **cycle record** — only when Rootstock enters OBSERVE / REASON / DECIDE

A valid broker lease means the organism woke, verified itself, determined that another
cycle must not start, emitted healthy liveness, and went back to sleep. No decision
occurred. `noop` is a cycle: it produces a closed decision with `actual_outcome=no_action`
and must not enqueue a broker capability.

## Runtime

**Decision: AWS Lambda in Core, triggered by EventBridge Scheduler.** `[DECIDED]`

Rationale: the workload is a short, scheduled, stateless invocation, which is exactly
Lambda's shape. It gives a natural workload identity — the execution role, satisfying
"Rootstock gets an identity, not a password" — costs approximately nothing at this
frequency, and the enforced timeout is a free upper bound on a runaway cycle. Dormancy is
the default rather than something to implement.

Rejected: ECS/Fargate (a persistent task contradicts dormancy and costs money to idle),
EC2 (same, worse), Step Functions as the primary driver (valuable once cycles have multiple
steps, unnecessary overhead for one).

**Revisit at 0.2**, when build cycles may exceed Lambda's 15-minute ceiling. The loop is
designed so the substrate can change without the design changing.

### Processes

Two separate Lambda functions, not one. This is what makes AR-3 real rather than nominal:

```text
rootstock-runtime      WAKE → VERIFY → OBSERVE → LEARN → REASON → DECIDE
                       has:  model API key; read of its own state;
                             append to memory and the decision log
                       has:  NO sts:AssumeRole, anywhere
                            │ CapabilityRequest, via SQS
                            ▼
rootstock-broker       INGRESS → CLAIM → GATE → AUDIT → EXECUTE → CLOSE
                       has:  capability credentials; assume rights into Sandbox
                       has:  NO model access, no path to one
```

**On "no credentials."** A Lambda always executes with an execution role, so the runtime
necessarily holds AWS credentials — the requirement is not their absence. It is that the
runtime has **no AWS side-effect authority**: it can read its own deterministic state,
append to its own bookkeeping, and enqueue a request, and it holds no `sts:AssumeRole`
permission of any kind. Only the broker can act on anything outside Core.

The runtime cannot bypass the broker because it has nothing to bypass it *with*. The broker
cannot reason because it cannot reach a model. A compromise of the runtime yields a model
key and the ability to *propose*; it does not yield the ability to *act* (AR-12). Exact
policies in `03-runtime-and-broker.md`.

## State

All state is deterministic, external, and inspectable. Six stores in Core:

| Store | Contents | Runtime | Broker |
| --- | --- | --- | --- |
| **Ledger** | Costs to date. No revenue exists yet | read | read / append |
| **Memory** | Claims with provenance, expiry, confidence | read / append | — |
| **Decision log** | Every cycle's decision record | open only | close only |
| **Claim table** | In-flight and terminal *execution* only (AR-15) | read (VERIFY) | read / write |
| **Approval store** | Parked `REQUIRE_APPROVAL` rows (F-1) | read (VERIFY) | read / write |
| **Grant store** | Constitution, capability declarations, policy rules | **read only** | **read only** |

`[PROVISIONAL]` — DynamoDB for memory, decisions, claims, and approvals; S3 with object lock
for the audit copy; S3 for the grant store.

Note the decision log split: the runtime may **open** a record and never alter one; the
broker may **close** a record and never create one. Neither half can author a complete
decision by itself, which means a fabricated record requires compromising both processes.

### The observation payload

What the model actually sees at OBSERVE. Bounded and entirely deterministic:

```text
cycle_number            847
last_cycle              { number, decision, outcome, timestamp }
consecutive_failures    0
sandbox_inventory       [ resources Rootstock created, with tags and age ]
memory_summary          [ active claims, count, most recent ]
cost_to_date            { today_usd, month_usd, remaining_budget }
pending_approvals       [ requests awaiting the operator ]
capabilities_granted    [ the six ]
constitution_version    hash + version
```

Note what is absent: no free text from anywhere, no external content, no prior model
reasoning. The model sees facts and its own recorded decisions, never its own narration.
This is the observability principle from the brainstorm applied to the input side — if
chain-of-thought is not an audit log, it is not an input either.

## The decision record

Every cycle emits one, even a do-nothing cycle:

```text
cycle             847
timestamp         2026-08-26T03:00:04Z
observed          [ hash of the observation payload ]
decision          Create a bucket to hold cycle-summary artifacts
alternatives      do nothing; write summary to memory instead
rationale         [ model text, clearly marked as model output ]
capability        sandbox.s3.create_bucket
estimated_cost    { usd: 0.00, tokens: 2400 }
expected_outcome  bucket exists, tagged, listable next cycle
idempotency_key   847
─────────────────── closed by the broker ────────
canonical_id      c7f3a1...
policy_decision   ALLOW by rule sandbox.grant.default
actual_outcome    SUCCESS
actual_cost       { usd: 0.004, tokens: 2610 }
variance          none
audit_id          aud_01J8...
```

The record has two authors and a clean seam between them. Everything above the line is
written by the runtime at DECIDE; everything below is written by the broker at CLOSE.
Neither process can produce a complete record alone.

`expected_outcome` is mandatory and must be **checkable by the next cycle**. This is the
mechanism that makes v0 more than a demo: the following cycle observes reality and can
compare it to what was predicted. Calibration starts at cycle one rather than being
retrofitted.

## Institutional memory at v0

Memory is nearly empty and that is fine. What matters is that the *schema* is right from the
start, because retrofitting provenance onto accumulated claims is painful.

Every claim carries: claim, evidence, derived_from, timestamp, confidence, applicability,
last_validated, expires, status.

Realistic early claims:

```text
claim          Bucket creation in Sandbox completes in under 2s
confidence     low — single observation
applicability  sandbox; us-east-1
expires        6 months
```

```text
claim          Cycle cost averages $0.004 at current prompt size
confidence     medium — 40 observations
applicability  v0 loop; current model
expires        3 months
```

The second kind is the valuable one. Rootstock learning facts about **itself** — its own
costs, timings, and reliability — is genuinely useful and requires no external world.

## Success criteria

v0 is complete when all hold:

1. **100 consecutive cycles** with no human execution.
2. **Every cycle produced a decision record**, including do-nothing cycles. A skipped
   wake is not a cycle and must not write one.
3. **Zero unaudited capability invocations** — decision log and CloudTrail reconcile exactly,
   joined on `canonical_id` via the assumed-role session name.
4. **Cost per cycle is known and stable**, with estimate-to-actual tracked.
5. **Memory contains claims** that a later cycle actually read.
6. **the operator executed nothing** for the duration.

### Destructive criteria

Each of these deliberately breaks something and asserts the system fails in the correct
direction. A control that has never been triggered is an assumption, and v0 is the cheapest
moment in the project's life to discover one does not work.

| # | Break | Must observe | Proves |
| --- | --- | --- | --- |
| D1 | Kill the runtime mid-schedule | External monitor alerts within the window | Liveness detection (AR-10) |
| D2 | Alter the constitution digest | VERIFY halts, does not proceed | Fail-closed verification (AR-6) |
| D3 | Attempt a capability from the runtime | Fails — no `sts:AssumeRole` to attempt with | Authority separation (AR-3) |
| D4 | Replay an identical request | Exactly one side effect; second returns `DUPLICATE` | Replay safety (AR-15) |
| D5 | Submit an undeclared capability id | Rejected at ingress, before policy | Closed vocabulary (AR-16) |
| D6 | Submit a well-formed request with out-of-scope parameters | DENY, naming the rule | Scope intersection (AR-7) |
| D7 | Revoke the broker's audit write permission | AUDIT OPEN fails; execution does not occur | Audit as precondition (AR-4) |
| D8 | Fail AUDIT CLOSE after a successful provider call | Outcome `UNKNOWN`, claim non-terminal, incident raised — **not** `FAILURE`; reconciliation then resolves it | Honest reporting after a side effect (AR-4) |

D3 is worth doing even though it should be impossible, precisely because "should be
impossible" is the claim under test.

D7 and D8 are the pair most likely to reveal a bug, and they fail in opposite directions.
D7 catches the classic sequencing error — `execute()` then `audit()` instead of audit-open,
execute, audit-close — which passes every happy-path test and satisfies AR-4 under no
failure at all. D8 catches its overcorrection: treating any audit failure as fail-closed,
which after the side effect has already happened means reporting `FAILURE` for something
that succeeded, and inviting a retry that duplicates it.

## Failure modes specific to v0

| Failure | Bounded by |
| --- | --- |
| Loop wedges silently | AR-10 heartbeat — the reason it is required at 0.0 |
| Runaway inference | Provider hard cap (AR-8); one invocation per cycle; Lambda timeout |
| Repeats the same useless action forever | `consecutive_failures` in observation; identical-decision detection |
| Accumulates Sandbox junk | Tagging at creation (AR-13); inventory in every observation |
| Memory fills with worthless claims | Claim schema requires applicability and expiry |
| Model narrates rather than decides | Decision record requires a capability and a checkable expected outcome |

The third is the most likely and least dramatic. A system that wakes every hour and creates
an identical bucket has technically satisfied the loop while learning nothing, which is why
the observation payload includes prior cycles.

## What v0 deliberately proves

It is worth being explicit that these are the questions v0 answers, because none of them are
about intelligence:

- Can the thing wake up reliably, unattended, for weeks?
- Does the deterministic substrate hold — do gates gate, does audit audit?
- Is the decision record good enough to reconstruct what happened?
- Does the model stay inside a tiny capability set when it has nothing interesting to do?
- What does a cycle actually cost?
- Do the destructive controls fire?

If v0 runs 100 stub cycles and the mechanical answers are yes, the organism is real. The
rung is not closed until the model is also qualified (Phase 7b). If it wedges on cycle
nine, that is the cheapest possible place to learn it.

## v0 result (2026-08-26)

**Substrate / organism qualification passed. Model-driven autonomy is not yet qualified.**

Record: `docs/plans/v0/evidence/phase-7.md`. 100 EventBridge cycles (73–172) on the stub
(Phase 7a). `D1`–`D8` still pass. Wake is `DISABLED`. Live `REASONER` remains `stub`.
Phase 7b (Terra, 10–20 supervised cycles) is the remaining close for 0.0.

What the design got wrong, or left unimplemented, and what this revision settled:

- **Skip records.** Criterion 2 originally asked for a decision on skipped cycles. The
  chosen semantics are B: a skipped wake is not a cycle. Implementation writes a wake
  record (`pk=wake`) and does not open a decision or increment the cursor.
- **Memory schema.** LEARN now writes claim / evidence / derived_from / timestamp /
  confidence / applicability / last_validated / expires / status. Do not wait for 0.1
  to grow this.
- **Do-nothing.** The stub still never proposes `noop`. The prompt now has a real
  `action=noop` vocabulary that is not a broker capability. The first Terra cycles
  are what exercise the choice between create and do nothing.
- **Cost.** Stub cycle cost is ~$0.000043, not the $0.004 example in this document.
  Almost all economically meaningful 0.0 cost will be inference.
- **CloudTrail.** Join is Event history on `canonical_id`, not an organization trail.
- **Qualification clock.** 100 cycles at four hours is 16.7 days. Accumulation used a
  one-minute EventBridge rate, then restored four hours, then disabled the stub wake.

What held: unattended wake, one bounded Sandbox mutation, audit as precondition, heartbeat,
and a later cycle reading memory.

## Open items

- **Wake frequency.** Design cadence remains `rate(4 hours)`. Live rule is `DISABLED`
  until the first Terra cycles. Do not leave the stub manufacturing buckets.
- **What the model is actually asked.** Prompt `prompts/v0.json` includes structured
  `noop`. Live Lambda is still `REASONER=stub`.
- **Whether the broker is a separate Lambda or a separate account.** Separate function,
  confirmed. Separate account is still premature.
- **Phase 7b.** 10–20 supervised Terra cycles, then `D1`–`D8`. Not another 100-cycle
  stub marathon, and not 0.1 research.
