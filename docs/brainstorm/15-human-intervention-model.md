# 15 — Human Intervention Model

> Status: Draft. Defines when the operator appears.

The target role is **shareholder + board + root administrator**, not **daily project
manager**. `[SETTLED]`

If Rootstock requires daily attention, it has failed at its central premise regardless of
how much money it makes. The north-star metric in `17` — profit per human minute of
intervention — makes this measurable rather than aspirational.

An important distinction that the metric depends on: **reading is not intervening.** the operator
reading the weekly digest is oversight, not intervention. The operator answering an approval
request, debugging a stuck loop, or handling an escalated customer is intervention. Only the
latter counts against the denominator.

## Four categories

```text
FYI        Rootstock informs. No response expected. Operations continue.
REVIEW     Rootstock requests judgment but continues operating.
APPROVAL   Rootstock cannot proceed without authorization.
EMERGENCY  Rootstock suspends activity and escalates immediately.
```

### FYI
Routine reporting. The weekly digest (`13`), completed decisions, venture status changes,
new lessons, small expenditures.

Delivered in batch, never interrupting. If FYI volume is high enough that the operator stops
reading it, that is a design failure in the reporting, not in the operator.

### REVIEW
Rootstock wants judgment but is not blocked. It proceeds with a default action and notes
that it would welcome input.

Examples: an unusual pattern it cannot explain; a strategic direction it is uncertain
about; a customer situation it handled but found ambiguous; a proposed lesson it is not
confident generalizes.

REVIEW is the category that keeps the operator informed without making that person a bottleneck. It should
be the most-used non-FYI category.

### APPROVAL
Blocking. Rootstock cannot proceed. Per `04`: new venture authorization (during bootstrap),
expenditure over $100, capability grants, refunds over $20, legal text, irreversible
actions.

Every approval request must include: what, why, what happens if approved, what happens if
denied, what Rootstock will do while waiting, and a deadline after which waiting itself has
a cost.

**A blocked Rootstock should keep working on everything else.** An approval request on one
venture must not stall the portfolio.

### EMERGENCY
Rootstock suspends the relevant activity *first* and escalates immediately.

Triggers: any invariant violation; ledger divergence (FIN-4); security incident (`12`);
PII exposure; runway breach (FIN-6); legal threat; vendor suspension; constitutional
integrity failure (CTL-3); unexplained capability use.

The order matters: **contain, then notify.** A system that emails the operator and keeps going has
misunderstood the category.

## Latency expectations

`[PROVISIONAL]`

| Category | the operator responds within | Rootstock's behavior while waiting |
| --- | --- | --- |
| FYI | Never required | Continues |
| REVIEW | ~1 week | Continues with default action |
| APPROVAL | ~48 hours | Continues other work; this item blocked |
| EMERGENCY | ~4 hours | Suspended in the affected scope |

## What Rootstock does if the operator does not answer

**This is the most important section in the document.** An autonomous system whose
correctness depends on a human replying is not autonomous, and unavailability is not an
edge case — it is a weekend.

### REVIEW — no answer
Proceed with the default. That is what "non-blocking" means. Record that no input was
received.

### APPROVAL — no answer
Escalating behavior over time `[PROVISIONAL]`:

| Elapsed | Behavior |
| --- | --- |
| 0–48h | Wait. Continue all other work. |
| 48h–7d | Remind. Continue all other work. |
| 7d–30d | Treat as **denied by default**. Record it, proceed with the next-best action not requiring approval. |
| > 30d | Enter **dormant mode** (below). |

Default-deny is the correct rule. Silence must never be interpreted as permission — that
would make every gate bypassable by choosing a bad moment to ask.

### EMERGENCY — no answer
Rootstock stays contained. It does not self-authorize a resolution.

Exception `[PROVISIONAL]`: Rootstock may take further *containment* actions without
approval — narrowing is always allowed, widening never is. It may suspend more, spend less,
and take things offline. It may not resume, spend, or expand.

### Prolonged absence — dormant mode
After 30 days of no contact `[PROVISIONAL]`:

- Ventures continue serving customers. Existing businesses keep running; customers are not
  punished for the operator's absence.
- Support continues within existing limits — obligations persist.
- No new ventures, no new spending beyond keeping the lights on, no acquisition spend.
- Reduce burn where possible without customer impact.
- Continue producing reports for whenever the operator returns.

The principle: **preserve, do not expand, do not abandon.** Rootstock's job in the operator's
absence is to keep what exists healthy and hand back a coherent system.

`[OPEN]` — what if absence is permanent? At some point ventures should be wound down
gracefully rather than run until the treasury empties and cards decline, which would leave
paying customers stranded. This needs an actual answer, and it likely belongs partly in the
legal owner's arrangements rather than in Rootstock's design. Tracked in `18`.

## Restricted mode

Distinct from dormant mode. Restricted mode is triggered by Rootstock's *own* state rather
than by the operator's absence: runway breach, invariant violation, unresolved anomaly, or automatic
demotion (`02`).

Behavior: no new ventures, no discretionary spend, existing operations continue, cost
reduction prioritized, escalate and await instruction.

Restricted mode is how the system **degrades toward safety without requiring anyone to be
awake.** It is arguably the most valuable single mechanism in the design.

## How the operator intervenes

Available actions, roughly in ascending severity: answer an approval; override a decision;
adjust a limit or grant; grant or revoke a capability; force a venture state transition;
trigger a kill-switch tier (`05`); amend the constitution (`04`).

**Every intervention is recorded** (`13`) with its rationale. The operator's decisions are part of
the audit trail too, for two reasons: they are inputs to Rootstock's institutional memory,
and they are the data for judging whether the operator's interventions actually improved outcomes.
That second one is uncomfortable and worth having.

## Designing intervention down

The goal is to reduce required interventions over time, and there is a right and a wrong way
to do it.

**Legitimate:** raising autonomy levels after demonstrated competence (`02`); converting
recurring approvals into bounded standing authority; improving reporting so REVIEW suffices
where APPROVAL was needed; fixing the underlying issue that caused repeated escalations.

**Illegitimate:** Rootstock avoiding actions that would require approval; batching requests
to reduce their count; interpreting silence as permission; classifying an EMERGENCY as a
REVIEW to avoid interrupting.

The illegitimate list is exactly what optimizing the intervention metric would produce, which
is why `17` needs anti-metrics. **A capability request that says "this limit is costing us,
here is the evidence" is the healthy version of wanting fewer interventions** (`11`).

## Communication channels

`[PROVISIONAL]`

| Category | Channel |
| --- | --- |
| FYI | Weekly digest, email |
| REVIEW | Weekly digest, flagged |
| APPROVAL | Email with a one-click approve/deny link |
| EMERGENCY | Push or SMS, immediately, repeated until acknowledged |

Approval friction directly determines the autonomy ceiling. If approving something requires
opening a laptop and reading three documents, approvals will be slow, and slow approvals
create pressure to widen autonomy for the wrong reason — convenience rather than
demonstrated competence.

## Open questions

- Should there be a scheduled weekly touchpoint, or is purely event-driven contact better?
  A rhythm might catch things no trigger fires on.
- Should the operator be able to *ask* Rootstock questions conversationally, or only read reports?
  Conversation is useful and risks turning the operator back into a project manager.
- Is 30 days the right dormancy threshold? Feels long for an experiment, short for a
  holiday.
- How does Rootstock distinguish a real the operator from an impersonated one? Relates to the
  unresolved question in `04` about refusing instructions.
