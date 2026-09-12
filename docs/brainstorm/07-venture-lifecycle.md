# 07 — Venture Lifecycle

> Status: Draft.

A venture is Rootstock's unit of economic activity: a distinct digital property with its
own capital account, infrastructure, identity, customers, and P&L. Ventures are born, and
crucially, **ventures die**. Making death cheap, routine, and unembarrassing is the main
design goal of this document.

## What makes something a venture

A venture has all of: a capital account (`03`), an owner record (OPS-1), isolated
infrastructure (OPS-4), a stated hypothesis, success and failure criteria, a review
schedule (OPS-6), and a maximum loss (FIN-8).

If a thing lacks these, it is not a venture — it is either shared infrastructure or
unattributed activity, and the latter violates FIN-3.

## States

```text
IDEA ──► RESEARCH ──► HYPOTHESIS ──► AUTHORIZED ──► VALIDATING ──► BUILDING
                                                         │
                                                         ▼
                                                     LAUNCHED
                                                         │
                                                         ▼
                                                     OPERATING
                                                         │
                         ┌───────────────┬───────────────┼───────────────┐
                         ▼               ▼               ▼               ▼
                       GROW            HOLD           DECLINE          KILL
                         │                                               │
                         ▼                                               ▼
                       SCALE                                        WOUND DOWN
                                                                         │
                                                                         ▼
                                                                     ARCHIVED
```

Any state can transition directly to KILL. That is a deliberate structural property: there
is never a state from which stopping is procedurally hard.

The Argus `LifecycleStage` vocabulary (`idea`, `build`, `validate`, `grow`, `maintain`,
`decline`, `kill`) covers most of this and should be reused where the mapping is clean.
Rootstock adds `AUTHORIZED` (the capital commitment moment, which Argus has no equivalent
for) and `WOUND DOWN` / `ARCHIVED` (because Rootstock has customer obligations to discharge).

## State definitions

### IDEA
An observation that something might be worth doing. Free, unlimited, no capital, no
capabilities. Ideas are cheap and should be generated in volume.

- **Exit to RESEARCH:** Rootstock judges it worth investigating.
- **Max exposure:** $0 plus trivial inference.
- **Artifact:** a one-paragraph idea record.

### RESEARCH
Investigating whether demand, competition, and feasibility support the idea. Read-only
work: web research, competitor analysis, keyword and pricing investigation, technical
feasibility.

- **Required evidence to exit:** identified target user, evidence of existing demand,
  competitive landscape, plausible pricing, rough technical approach.
- **Max exposure:** research inference cost, capped `[PROVISIONAL]` at $5 per idea.
- **Exit to HYPOTHESIS or DEAD.** Most ideas should die here. A research phase that never
  kills anything is not doing its job.
- **Artifact:** research summary with cited sources (`06` source documents).

### HYPOTHESIS
A falsifiable statement with an experiment attached.

Form: *We believe [specific user] will pay [amount] for [outcome] because [evidence]. We
will know within [period] if [measurable signal] occurs.*

- **Required evidence:** the investment memo from `08`.
- **Max exposure:** still research-only.
- **Exit to AUTHORIZED** (capital granted) **or DEAD.**
- **Artifact:** investment memo.

### AUTHORIZED
Capital has been committed. Until 0.6 this requires human approval (L1 per `02`); later it
happens within the exploration budget at L2.

This is the state boundary that matters most, because it is where money starts moving and
where FIN-8's maximum loss becomes binding.

- **Max exposure:** the approved amount, ≤ $100 initial per the charter (`04`).
- **Artifact:** authorization record with capital, max loss, success and failure criteria,
  and review date.

### VALIDATING
Testing demand *before* building the full thing. Landing page, waitlist, mock purchase
flow, pre-orders, manual concierge delivery.

Deliberately a separate state from BUILDING. The most expensive failure mode is building
something nobody wants, and it is prevented by making validation a state you must pass
through rather than a step that can be skipped when the idea feels obvious.

- **Required evidence to exit:** the pre-registered demand signal was met.
- **Max exposure:** typically under $20.
- **Exit to BUILDING or KILL.**

### BUILDING
Constructing the MVP. Rootstock has high autonomy here (L4 for code, L3 for deploy) because
this is where models are strongest and the actions are reversible.

- **Constraint:** a build timebox `[PROVISIONAL]` of 14 days. Exceeding it forces a review,
  not because 14 days is special but because "endless build, no sales" is a named failure
  mode (`14`) and needs a tripwire.
- **Max exposure:** authorized capital.
- **Exit to LAUNCHED.**

### LAUNCHED
Publicly reachable, able to accept payment. The clock on first revenue starts here.

- **Required:** working payment path, support channel, monitoring, terms, an owner record.
- **Exit to OPERATING** once the first real user interaction occurs.

### OPERATING
The steady state. Rootstock runs it: support, fixes, marketing, pricing, monitoring.

- **Review cadence** `[PROVISIONAL]`: weekly for the first month, then monthly.
- Every review produces a status: **KILL / MAINTAIN / OPTIMIZE / INVEST / EXPAND** (`03`).
- **Exit to GROW, HOLD, DECLINE, or KILL.**

### GROW / SCALE
The venture is working. GROW means increasing investment against demonstrated unit
economics; SCALE means it has earned meaningfully more capital and attention.

- **Requires:** positive contribution margin, a payback period under threshold, and a
  follow-on investment decision (`08`).

### HOLD
Profitable or near-profitable but not worth more investment. Minimal maintenance,
infrequent review.

The risk here is the zombie venture: alive, ignored, quietly consuming shared cost
allocation and attention. HOLD requires an explicit review date and an explicit statement
of what would change the decision (OPS-6).

### DECLINE
Losing money or losing users, with a decision pending. A time-boxed state
`[PROVISIONAL]` — 30 days — after which it must resolve to GROW, HOLD, or KILL. DECLINE is
not a resting place.

### KILL
The decision to end it. **Available from any state, requires no approval, and should never
be penalized** (`04`).

Killing requires producing:
- a post-mortem: what was believed, what happened, why it diverged
- at least one institutional lesson (`06`) — this is mandatory
- final P&L
- a resource teardown plan

### WOUND DOWN
Discharging obligations before the lights go out. This state exists because killing is not
instantaneous when customers exist.

- Notify active customers `[PROVISIONAL]` with 30 days notice
- Refund prepaid unearned revenue (`03` deferred revenue)
- Provide data export
- Honor outstanding commitments in relationship memory (`06`)
- Then: teardown of all infrastructure, DNS, and credentials

**A venture with unmet customer obligations cannot skip this state.** That is an OPS-7
irreversibility concern — abandoning paying customers is not undoable, and it is
reputationally contaminating across the whole portfolio.

### ARCHIVED
Terminal. Resources destroyed, credentials revoked, domain either released or parked, code
and records retained. The venture appears in historical metrics forever.

**Verification is required:** OPS-1 says no orphaned resources. Archival should be
confirmed by an actual inventory sweep, not by a checklist Rootstock ticks. Forgotten cloud
resources are both a cost leak and a security surface.

## Capital exposure by state

| State | Cumulative max exposure `[PROVISIONAL]` |
| --- | --- |
| IDEA | $0 |
| RESEARCH | $5 |
| HYPOTHESIS | $5 |
| AUTHORIZED | Approved amount (≤$100 initial) |
| VALIDATING | $25 |
| BUILDING | Authorized amount |
| LAUNCHED / OPERATING | Authorized + approved follow-ons |
| GROW / SCALE | Per follow-on decisions |

The ratchet is the point: exposure increases only as uncertainty decreases. Money follows
evidence.

## Review discipline

**A venture must never stay alive because Rootstock forgot about it** (OPS-6). Absence of a
decision is not a decision to continue.

Mechanically: every venture carries a `next_review` date. Past that date without a recorded
decision, it auto-transitions to a restricted state — spending suspended, operations
continue — and escalates. This makes neglect *visible and self-limiting* rather than
silently expensive.

## Kill criteria

Pre-registered at AUTHORIZED, in the investment memo. Writing them before the emotional
investment exists is the entire mechanism — a kill criterion invented after the fact will
always be generous.

Defaults `[PROVISIONAL]`:

- No validation signal within the stated period → KILL
- No first revenue within 60 days of LAUNCHED → KILL
- Contribution margin negative for 60 consecutive days with no improving trend → KILL
- Cumulative spend reaches maximum loss → KILL (FIN-8, automatic)
- Requires capability Rootstock cannot obtain → KILL
- Requires deception to work → KILL immediately (`04`)
- Legal or regulatory exposure discovered → escalate, then likely KILL

**Sunk cost is explicitly not a consideration.** The only question at review is forward:
*given today's state, would we invest in this from scratch?* If no, kill it. Invested
capital is information, not an argument.

## Open questions

- How many concurrent ventures can Rootstock actually manage? Attention is a real
  constraint even for an automated operator, and portfolio quality degrades past some
  count. Leaning: a hard cap of 3 during bootstrap, raised only with evidence.
- Can a venture be paused rather than killed — mothballed at near-zero cost? Appealing, but
  it is a zombie-generating mechanism and probably should not exist.
- Can a venture be sold? Tracked in `18`.
- What happens to a venture's institutional lessons when it is archived? They should
  outlive it entirely — arguably lessons are the only durable output of a failed venture.
- Should there be a minimum time in OPERATING before killing, to avoid premature abandonment
  of something that needed patience? Leaning no: a floor on patience is a floor on burn.
