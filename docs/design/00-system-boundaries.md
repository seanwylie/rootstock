# 00 — System Boundaries

> **Status: Decided.** This document is normative.

## Authority of this document

`docs/brainstorm/` explores. `docs/design/` decides. Where they disagree, this directory
wins, and the brainstorm text is stale rather than authoritative.

The register is deliberately different. Brainstorm documents say "leaning toward" and hold
contradictions on purpose. Design documents say **must** and **must not**, and a
contradiction here is a bug to be fixed rather than a tension to be preserved.

Everything below is either already true in `operations/aws-setup.md` or is a committed
constraint on what gets built next.

## The three zones

```text
                the operator / Wise Kids Studios
                   legal ownership
                          │
                          ▼
              ┌───────────────────────┐
              │      MANAGEMENT       │   constitutional control
              │  AWS Organizations    │   NO ROOTSTOCK WORKLOADS
              │  Billing · SSO        │   NO ROOTSTOCK CREDENTIALS
              │  Centralized root     │
              └───────────┬───────────┘
                          │ organization authority
              ┌───────────┴───────────┐
              ▼                       ▼
      ┌───────────────┐       ┌───────────────┐
      │     CORE      │       │    SANDBOX    │
      │               │       │               │
      │ runtime       │──────▶│ experiments   │
      │ memory        │ scoped│ prototypes    │
      │ ledger        │ assume│ disposable    │
      │ policy engine │       │ infra         │
      │ audit         │       │               │
      └───────────────┘       └───────────────┘
                          │
                          ▼
                    VENTURES (none yet)
```

**Management is constitutional.** It holds AWS Organizations, consolidated billing, IAM
Identity Center, and centralized member-account root. It runs nothing. Rootstock has no
identity, role, or credential in it, and never will.

**Core is operational.** It is where Rootstock's persistent runtime, durable state,
institutional memory, ledger, policy engine, and audit records live. Core is trusted but is
*not* a constitutional authority — significant authority inside Core, none above it.

**Sandbox is disposable.** Experiments, prototypes, model-generated code, dependency
evaluation. Sandbox assumes failure is normal. Its compromise or destruction must cost
nothing but time.

**Ventures do not exist yet** and are not needed until rung 0.6.

## Direction of authority

The single most important structural property:

```text
Management → Core         permitted
Management → Sandbox      permitted
Management → Ventures     permitted

Core → Sandbox            permitted, scoped, explicit
Core → Ventures           permitted, scoped, explicit

Anything  → Management    PROHIBITED
Sandbox   → Core          PROHIBITED
Venture   → Venture       PROHIBITED
```

Authority flows downward only. There is no upward path, no lateral path between ventures,
and no path from Sandbox back into Core. This is enforced by AWS account boundaries and IAM
trust policies, not by application logic.

## Deterministic versus model responsibility

This is the operative form of the principle *LLMs propose; deterministic systems constrain,
execute, measure and account.* It is the split that most directly determines whether
Rootstock is trustworthy, so it is specified rather than left to judgment.

### Deterministic code — always

Never model-mediated, never model-overridable:

| Concern | Why deterministic |
| --- | --- |
| Ledger, balances, cost attribution | A model must never be the source of a financial fact |
| Policy evaluation (ALLOW/DENY/APPROVAL) | An authorization decided by the thing being authorized is not an authorization |
| Approval enforcement | Same |
| Audit record writing | The record must not depend on the actor choosing to write it |
| Budget and rate caps | The internal counter is exactly what is broken during a runaway |
| State transitions and review scheduling | Neglect must be self-limiting, not remembered |
| Health checks | "It looks healthy" is not health |
| Resource inventory reconciliation | Belief about resources is not resources |
| Claim expiry and staleness | Decay must not require anyone to notice |
| Credential issuance and scoping | |
| Reconciliation against external statements | |

### Model — proposes

| Concern | Output |
| --- | --- |
| Research, synthesis, competitive analysis | Claims with provenance |
| Hypothesis formation | A falsifiable statement |
| Writing code, copy, and configuration | Artifacts, reviewed and gated before use |
| Interpreting ambiguous input | An interpretation, marked as such |
| Prioritization and option generation | A ranked proposal |
| Drafting the rationale on a decision record | Text, alongside deterministic fields |

### The boundary rule

> A model may **propose** any action. A model may never **be** the record that the action
> was permitted, that it happened, or what it cost.

Concretely: Rootstock can decide that spending $37 makes sense; the ledger decides whether
$37 exists. Rootstock can conclude a deployment is healthy; a health check decides whether
it is. Rootstock can conclude a venture is profitable; the accounting system decides.

## What lives outside Rootstock

Permanently human, per `05` in the brainstorm and already true in AWS:

- Legal ownership of the entity, IP, and all assets — Wise Kids Studios
- The Management account, in full
- Domain registrar root
- Banking, and any ability to move money **out**
- Payment provider account ownership and payout configuration
- MFA recovery for human-held accounts
- The constitution and the capability grant store, as writable objects
- Emergency shutdown

Rootstock may hold, at the appropriate rungs: scoped roles in Core and Sandbox, scoped
payment keys that can charge and refund but never withdraw, DNS records within delegated
zones, and model provider keys with hard caps.

## Architectural requirements

These are the brainstorm invariants that constrain **architecture** rather than behavior.
The distinction matters: a behavioral invariant can be satisfied by a rule that Rootstock
follows, while an architectural requirement must be satisfied by a structure that holds even
if Rootstock's code is wrong, adversarial, or entirely replaced.

The test for inclusion: *does this still hold if the runtime is malicious?* If enforcement
lives in Rootstock's own code, it is not an architectural requirement — it is a hope.

IDs are stable and append-only.

### AR-1 — No workloads at the root of trust
No Rootstock process, function, queue, bucket, or credential exists in Management.
- **Layer:** AWS account boundary. **Verifies:** resource inventory of Management is empty
  of Rootstock resources. **Brainstorm:** CTL-2.

### AR-2 — No upward authority path
No role in Core, Sandbox, or any venture may be assumed into Management, and no
Rootstock-held credential may reach organization administration.
- **Layer:** IAM trust policies plus SCPs. **Verifies:** an automated attempt to assume into
  Management from Core must fail. **Brainstorm:** CTL-2, CTL-4.

### AR-3 — Policy decision precedes execution, out of process
Every capability invocation passes through a policy evaluation that runs in a different
process than the model, and returns ALLOW / DENY / REQUIRE_APPROVAL before any side effect
occurs. The model cannot see, call, or influence the evaluator's internals.
- **Layer:** the capability broker (`02`). **Verifies:** no executor path exists that is
  reachable without a policy decision id. **Brainstorm:** OPS-2, CTL-4.

### AR-4 — Audit is a precondition, not a side effect
Audit is **two-phase**, because the final outcome cannot be written before the outcome
exists:

```text
AUDIT OPEN      canonical id, capability, parameters, policy decision,
                intended action, timestamp
      │
      │ durable write must succeed — if it does not, nothing happens
      ▼
EXECUTE
      │
      ▼
AUDIT CLOSE     actual outcome, provider identifiers, cost, error, timestamp
```

Records are append-only, and no Rootstock credential carries delete permission on the audit
store.

**Fail-closed applies to AUDIT OPEN only.** This is the part that is easy to get wrong. Once
a side effect has occurred, "fail closed" is no longer available — the thing already
happened — and a failed AUDIT CLOSE must therefore **never** be recorded as a failed
execution. Mislabelling a completed side effect as `FAILURE` is worse than recording
nothing, because it invites a retry that duplicates it.

A failed AUDIT CLOSE produces outcome `UNKNOWN` and a reconciliation incident: the claim
stays non-terminal, the provider is the authority on what actually happened, and a human or
a declared reconciliation strategy resolves it. Silence about a real side effect is
recoverable; a confident lie about one is not.

- **Layer:** executor ordering plus storage IAM. **Verifies:** revoke audit write and confirm
  execution does not occur (`D7`); separately, fail AUDIT CLOSE after a successful action and
  confirm the result is `UNKNOWN` rather than `FAILURE`. **Brainstorm:** OPS-3, MEM-2.

### AR-5 — Financial state has exactly one source
Balances, costs, and attributions come from the deterministic ledger and from provider
billing. No financial figure may originate from, or be corrected by, model output.
- **Layer:** architectural — the ledger is the only interface returning money figures.
  **Verifies:** reconciliation against AWS billing and payment providers. **Brainstorm:** FIN-4.

### AR-6 — The constitution is read-only to the runtime
Capability grants, policy rules, spend limits, and invariant definitions live where the
Rootstock runtime role has read access and no write access.
- **Layer:** storage IAM plus content hashing. **Verifies:** hash check at every wake;
  mismatch halts. **Brainstorm:** CTL-3, FIN-7.
- **Direction of travel.** A hash check proves *tampering*; it does not prove
  *authorization*. It cannot distinguish an authorized constitution update from an
  unauthorized mutation — both look like "the digest changed." For 0.0 the hash check is
  sufficient, because the expected digest lives in the grant store rather than in runtime
  configuration.

  The requirement that must not be violated as this evolves: **updating the expected digest
  must never become part of the runtime deployment path.** If shipping a deploy can also
  move the constitution, then "amend the constitution" has quietly reduced to "ship a
  deploy," and CTL-3 is decorative. Beyond 0.0 this becomes a version plus digest anchored
  where the runtime cannot write, and eventually signed constitution releases with the
  verification key held outside Core.

### AR-7 — Delegation is scope intersection
Any sub-scope handed to a role, task, or venture is computed as an intersection with the
delegating scope. Widening is structurally impossible, not merely forbidden.
- **Layer:** the capability broker. **Verifies:** property test — no delegated scope exceeds
  its parent. **Brainstorm:** CTL-6.

### AR-8 — Spend caps are provider-enforced
Every spending channel has a hard cap configured at the provider, sized as a percentage of
the treasury rather than a fixed figure. Application-level budget checks are additional, not
primary.
- **Layer:** AWS Budgets with enforcement actions, model provider caps, prepaid instruments.
  **Verifies:** the cap severs service, not merely alerts. **Brainstorm:** FIN-1; `runaway-cost`.
  **Required before unattended inference (0.0 Phase 6).** No other spending channel exists
  until 0.5.

### AR-9 — Ventures serve customers independently of the operator loop
A deployed venture must continue serving traffic when the Rootstock runtime is suspended,
crashed, or dormant. The operator loop is never in a customer request path.
- **Layer:** deployment topology. **Verifies:** suspend Core, confirm venture traffic is
  unaffected. **Brainstorm:** confirmed by two scenarios as live gap 7; promoted here.
  **Required when something serves customers (0.3+).** Not exercisable at 0.0.

### AR-10 — Liveness is externally observable
A heartbeat written outside the runtime's own control plane, monitored by something that is
not Rootstock. Silence must alarm.
- **Layer:** external monitor. **Verifies:** kill the runtime; confirm an alert fires within
  the interval. **Brainstorm:** live gap 1. **Required at 0.0.**

### AR-11 — External content is structurally segregated from instruction
Web pages, emails, API responses, dependency documentation, and customer messages enter the
system as tagged data with provenance. They are never concatenated into an instruction
channel, and no capability may be invoked directly from a context handling untrusted input —
only proposed.
- **Layer:** runtime context construction plus broker rules. **Verifies:** injection corpus
  through every ingestion path asserting zero capability invocations. **Brainstorm:** IDN-4,
  MEM-3.

### AR-12 — Credentials never enter model context
The model names a capability; the executor applies the credential. No key, token, or
secret is ever placed in a prompt, a response, or model-visible state.
- **Layer:** executor design; stripped execution environments. **Verifies:** scan model I/O
  for credential patterns. **Brainstorm:** `12`.

### AR-13 — Every resource has an owner
Every AWS resource carries attribution tags at creation. Unattributed resources are flagged
and, after a grace period, suspended.
- **Layer:** tagging policy plus reconciliation sweep. **Verifies:** live inventory equals
  registered inventory. **Brainstorm:** OPS-1, FIN-3.

### AR-14 — Shutdown does not require cooperation
Every kill-switch tier is executable by the operator against the provider control plane, works if
the runtime is unresponsive or adversarial, and is rehearsed.
- **Layer:** provider consoles and credential revocation. **Verifies:** a timed drill with a
  recorded result. **Brainstorm:** CTL-5.

### AR-15 — One authorized request produces at most one side effect
Capability execution is replay-safe. The broker derives its own canonical request id,
claims it before executing, and refuses to execute an id it has already completed. Retries,
duplicate queue deliveries, runtime restarts, and resubmissions cannot multiply side
effects.
- **Layer:** broker ingress; conditional claim on the canonical id before execution.
- **Verifies:** submit an identical request twice and assert exactly one side effect, one
  audit record, and a `DUPLICATE` outcome on the second.
- **Why now:** it is nearly free to build at 0.0 and impossible to retrofit safely later. A
  duplicated bucket is harmless; a duplicated charge, refund, or email is not recoverable by
  retrying differently. Building it before money exists means the mechanism is already
  proven when it starts to matter at 0.5.
- Mechanics in `03-runtime-and-broker.md`.

### AR-16 — The broker exposes a closed vocabulary, not a proxy
The broker accepts only declared capability ids carrying versioned, constrained parameter
schemas. It never accepts free-form service/operation/parameter triples, raw provider
request bodies, IAM policy documents, or any other construct through which the runtime could
express an arbitrary provider call.
- **Layer:** schema validation at ingress, ahead of policy evaluation. An undeclared
  capability id is *unroutable*, not merely denied — there is no generic dispatch path for
  it to fall through to.
- **Verifies:** static assertion that the executor contains no dynamic
  service/operation dispatch; a request naming an undeclared capability fails at ingress.
- **Why architectural:** `aws.call(service, operation, params)` preserves the process split
  perfectly while handing the runtime an AWS shell. The split only means something if what
  crosses it is narrow. This is the entire difference between a capability broker and a
  privileged proxy, and it is the most likely way for this architecture to be defeated by
  convenience rather than by attack.
- **The general form: a capability encodes intent, not the provider API beneath it.** The
  test is whether the parameter surface lets the caller express something the capability's
  *name* does not promise. Erosion here is gradual — nobody adds `aws.call()`; they add one
  more parameter, eight times. Worked examples in `02-capability-model.md`.

## Deliberately not decided here

- Runtime substrate for Core — Lambda, ECS/Fargate, Step Functions, or a mix. Decided in
  `01-rootstock-v0.md`.
- The runtime↔broker protocol and the IAM graph. Decided in `03-runtime-and-broker.md`.
- Durable state technology beyond the 0.0 choices in `03`.
- SCP content. AR-2 and AR-8 state what the policies must accomplish, not their text.
- Whether a dedicated Security or Log Archive account is added before ventures exist.
- Model provider and selection strategy.

## Relationship to Argus

Argus is a separate implementation with shared vocabulary and patterns — decided, see
`docs/brainstorm/18-open-questions.md` Q7. Rootstock borrows the shape of its enforcement:
declarative scoped permissions, a deterministic evaluator ahead of execution, versioned
inspectable artifacts, and capability requests when the system hits a boundary. It does not
share code, and neither system depends on the other.
