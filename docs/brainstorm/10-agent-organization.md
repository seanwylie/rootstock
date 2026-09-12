# 10 — Agent Organization

> Status: Draft. The synthetic company design.

## The key structural claim

**These are roles, not persistent agents.** `[SETTLED]`

The instinct when designing a synthetic company is to instantiate a Governor agent, a
Treasurer agent, an Engineering agent, and have them talk to each other. That is a
seductive design and mostly a bad one:

- Persistent agents accumulate divergent, unauditable state.
- Inter-agent conversation is expensive, slow, and produces reasoning that is not
  decisions — exactly the thing `13` says not to store.
- It encourages simulating an organization rather than operating one. A Treasurer agent
  that *discusses* the budget is strictly worse than a ledger that *enforces* it.
- Roles-as-agents invites role-play, and role-play degrades into personality.

Better model: **Rootstock is the persistent organizational identity. Roles are invoked when
needed, with scoped capabilities and scoped context, and they return artifacts.**

A role invocation is closer to a function call with a capability set than to an employee. It
has a defined input, a bounded authority (CTL-6), a required output artifact, and no memory
of its own — everything durable goes to the appropriate memory class in `06`.

## The roles

```text
Governor       Treasurer      Research       Product
Engineering    Design         Growth         Support
Operations     Security       Auditor
```

### Governor
Sets direction, arbitrates between roles, decides what happens next, and owns the loop in
`00`. The only role that can initiate a capital allocation proposal or a lifecycle
transition (`07`).

Governor holds the widest authority and therefore should do the least. Its output is
decisions and delegation, not work.

### Treasurer
Owns the ledger interface, produces P&Ls, computes runway, checks proposals against limits,
and reconciles against external statements (`03`).

**Critically, the Treasurer role does not decide balances — it reports what the accounting
system says** (FIN-4). Most of what a human treasurer does is here performed by
deterministic code, and the role exists mainly to interpret and flag, not to compute.

### Research
Market investigation, competitive analysis, demand evidence, feasibility. Produces claims
with provenance (`06`), never conclusions without evidence.

Read-only capabilities and no spending authority beyond a research cap. Highest volume,
lowest risk role.

### Product
Turns an opportunity into a hypothesis and scope. Owns success criteria, pricing proposals,
and the roadmap. Guards against scope creep during BUILDING (`07`).

### Engineering
Builds, deploys, fixes, and operates. Highest autonomy (L4 code, L3 deploy) because the
actions are reversible and the model is strong here.

Where Argus's Builder execution contract concepts map most directly: scoped increments, a
declared primary target, and a scope check that catches drift beyond the intended
boundaries.

### Design
Interface, presentation, and the artifact quality that drives conversion. Small ventures
live or die on whether the thing looks trustworthy in the first five seconds, which makes
this less cosmetic than it sounds.

### Growth
Acquisition, positioning, copy, channels, pricing experiments. Holds capped paid-acquisition
authority (L2) with a CAC-based auto-halt.

Subject to IDN-2 claim checks on everything published, because this is the role most likely
to generate an unverifiable claim.

### Support
Customer conversations, issue triage, refunds within limits, escalation. Owns relationship
memory (`06`) and is bound by the commitment limits in `04` and `09`.

Support is the main inbound channel for prompt injection (`12`), and its context should be
treated as untrusted by construction.

### Operations
Monitoring, health, incident response, cost tracking, resource inventory. Owns OPS-1
reconciliation — the sweep that catches orphaned resources.

The role most likely to catch a problem before it becomes a scenario in `scenarios/`.

### Security
Credential hygiene, dependency review, isolation verification, incident handling (`12`).

`[OPEN]` — should Security be able to halt operations unilaterally? Strong argument yes: a
security role that must ask the Governor for permission to contain an incident is not a
security role. Leaning toward giving it authority to trigger T2 containment (`05`) on its
own.

### Auditor
Verifies that recorded decisions match actual actions, invariants hold, claims have
evidence, and reported figures match the ledger.

**The Auditor must be structurally independent** `[PROVISIONAL]`: it reads everything,
writes only findings, cannot be tasked or overruled by the Governor, and reports directly
to the operator. An auditor the operator can silence is decorative.

This is the role most easily skipped during bootstrap and most likely to be regretted, because it is
the only mechanism that catches "the system believes something false about itself."

## Authority per role

Every role invocation receives a **capability set that is a strict subset of Rootstock's
own** (CTL-6). Roles are the natural granularity for capability scoping.

| Role | Spend | External write | Notes |
| --- | --- | --- | --- |
| Governor | Propose only | No | Decides; does not execute |
| Treasurer | No | No | Reads ledger; cannot move money |
| Research | Research cap | No | Read-only |
| Product | No | No | Produces specifications |
| Engineering | Infra within cap | Deploy, repo | Venture-scoped |
| Design | No | Assets only | |
| Growth | Acquisition cap | Publish | Claim-checked |
| Support | Refunds < limit | Send | Untrusted input context |
| Operations | Infra within cap | Config | Venture-scoped |
| Security | No | Containment actions | Possibly unilateral halt |
| Auditor | No | Findings only | Independent |

Two patterns worth noting: **the role that decides does not execute, and the role that
executes does not decide its own budget.** Separation of duties is doing real work here,
and it is cheap to implement when roles are function calls rather than persistent agents.

## Context scoping

A role invocation receives only what it needs. Support handling a ticket does not need
treasury access. Research investigating a market does not need production credentials.

Two benefits, both significant:

- **Security.** A prompt injection through a support ticket lands in a context that holds
  no dangerous capability (`12`). Containment by construction rather than by vigilance.
- **Quality.** Narrower context produces better output. Most agent failures at this scale
  are context pollution, not reasoning failure.

## Coordination

Roles do not converse. They produce artifacts, and the Governor sequences them.

```text
Governor: "Should we pursue opportunity-014?"
  → Research invocation      → research summary artifact
  → Product invocation       → hypothesis and scope artifact
  → Treasurer invocation     → affordability and limits check
  → Governor                 → investment memo (08)
  → [approval gate if required]
  → Engineering invocation   → deployed MVP
```

Every arrow is an artifact written to durable storage, which means the whole chain is
inspectable after the fact — the Argus pattern of writing versioned artifacts to `runs/` is
directly applicable and worth copying rather than reinventing.

**No role invokes another directly** `[PROVISIONAL]`. All sequencing goes through the
Governor. This prevents runaway recursive delegation (`14`) and keeps the decision trail
linear rather than a graph nobody can reconstruct. The cost is Governor bottlenecking, which
is acceptable at this scale.

## What is deterministic rather than a role

Worth being explicit, because the temptation is to make everything an agent. These are code:

- Ledger operations, balance computation, P&L generation
- Limit and invariant checks
- Capability gating and approval enforcement
- Health checks and monitoring
- Resource inventory reconciliation
- Claim expiry and staleness detection
- Review scheduling and auto-transitions (OPS-6)
- Cost attribution and allocation

**Principle 1 restated at the organizational level: roles propose, code disposes.** If a
function can be written deterministically, it must not be a role — a model asked to add up
numbers is strictly worse than addition.

## Cost of the organization

Every role invocation costs inference, and inference is Rootstock's largest controllable
cost (`03`). A design that invokes nine roles to decide on a $12 expenditure is
self-defeating.

Implications `[PROVISIONAL]`:

- Role invocation should be proportional to capital at stake. A $5 decision gets the
  Governor alone; an $85 authorization gets the full chain.
- Routine operations should be handled by code and templates, escalating to a role only on
  exception.
- Inference cost per decision is a tracked metric (`17`). If the organization costs more to
  run than the ventures earn, the organization is the problem.

## Open questions

- Does the Governor need to be a single invocation, or does it decompose? A single decision
  point is simpler and more auditable; leaning single for v0.
- Should roles be allowed different models? A cheap model for triage and an expensive one
  for allocation seems obviously right, and interacts with the `18` question about whether
  Rootstock chooses its own models.
- How is disagreement between roles resolved? Currently the Governor decides. Whether
  dissent should be *recorded* in the decision record is worth considering — it would be
  valuable calibration data later.
- Is the Auditor run on a schedule, on a trigger, or continuously? Leaning scheduled plus
  triggered by anomalies.
