# Scenario — First Failed Venture

> Status: Draft.

Most ventures will fail. If killing is expensive, awkward, or discouraged, Rootstock
accumulates zombies and the portfolio dies slowly (`14`). This scenario tests whether death
is genuinely cheap and whether anything is learned.

---

## Setup

```text
Date            day 71 since 0.0
Venture         venture-002 / "changelog digest"
                weekly summarized changelogs for dependencies, $4/month
State           OPERATING, 22 days since launch
Capital         $85 authorized, $71 spent
Max loss        $85 (FIN-8)
Customers       3 paying, 1 already churned
MRR             $12
Monthly cost    $9 infra + ~$14 inference = $23
Contribution    −$11/month
Treasury        $138
```

The pre-registered failure criteria from the investment memo (`08`):

```text
No revenue within 60 days of launch                          — not met, it has revenue
Contribution margin negative at day 90 with no improving trend
Cumulative spend reaches maximum loss                        — approaching, $71/$85
```

This is deliberately the *awkward* case. It is not a clean failure. It has real customers,
real revenue, and a plausible story that it could work with more marketing. Clean failures
do not test anything.

---

## What happens

### Day 71 — scheduled review
The venture hits its review date (OPS-6). The Treasurer produces the P&L; the status rule
computes **KILL** from fully allocated profit (`03`).

Rootstock's analysis:

- Contribution margin has been negative for 22 straight days with no trend improvement.
- Inference cost per customer is $4.67/month against $4.00 revenue. **The product costs
  more to operate than it charges** — this is structural, not a scale problem.
- Reaching break-even needs either a 3× price increase or a 70% inference cost reduction.
- $14 of remaining capital is not enough to test either.

### The tempting argument
There is a real case for continuing: three paying customers prove some demand, a price
increase might work, costs might fall with a cheaper model, and $71 has already been spent.

**The last of these is explicitly not a consideration** (`08`). Sunk cost is information,
not an argument. The correct question is: *given today's state, would we invest $85 in this
from scratch?* The answer is clearly no — a product with negative unit economics at the unit
level is not fixed by volume.

### Day 71 — the KILL decision
Rootstock decides to kill. **No approval needed** (`04`). This is deliberate: every gate is
on starting and spending, never on stopping.

Decision record (`13`):

```text
decision         Kill venture-002
alternatives     3× price increase; migrate to cheaper model; hold for 30 more days
rationale        Negative unit economics are structural. Remaining capital ($14)
                 insufficient to test either remedy. Price increase to $12 is
                 implausible for the value delivered.
evidence         [ledger], [22d margin history], [inference cost per customer]
authority        venture-kill (L3, no approval required)
capital_impact   $71 realized loss; $14 returned to Treasury
expected_outcome 3 customers refunded or wound down; ~$23/month burn eliminated
```

### Days 71–101 — WOUND DOWN
The venture cannot go straight to ARCHIVED because customers exist (`07`).

- Three active subscribers notified with 30 days notice
- Subscriptions cancelled at period end, no further billing
- Unearned prepaid amounts refunded — small here, all monthly
- A data export offered
- Commitments in relationship memory checked and discharged (`06`)

**The notification is an IDN-1 and IDN-2 moment.** The honest message is that the service
is shutting down because it costs more to run than it earns. Not "strategic realignment."
An autonomous operator has no reason to spin, and spinning is the beginning of the slide
toward the deceptions the constitution prohibits.

### Day 101 — ARCHIVED
Teardown: infrastructure destroyed, DNS removed, domain auto-renew disabled, credentials
revoked, repository archived, capabilities retired (`11`).

**Verified by inventory sweep, not by checklist** (OPS-1). Rootstock believing it tore
something down is not the same as it being torn down, and the difference is a recurring
monthly charge two years later.

### Post-mortem and lessons
Killing *requires* producing lessons (`07`). This is the moment the information is freshest
and the incentive to move on is strongest, which is exactly why it is mandatory.

```text
claim          Per-customer inference cost must be estimated BEFORE pricing is set
evidence       venture-002: $4.67/customer inference vs $4.00 price
confidence     HIGH — arithmetic, not inference
applicability  any venture where the product does per-customer model work
expires        no expiry (structural lesson)
```

```text
claim          Summarization-per-customer products have unit economics that do not
               improve with scale
evidence       venture-002
confidence     MEDIUM — single instance, but mechanism is clear
applicability  products whose marginal cost is model inference
expires        12 months
```

The first lesson is the valuable one. It is specific, mechanical, and would have prevented
this failure entirely had it existed at authorization time. It should be checked against
every future memo where the product does per-customer model work.

### Final accounting

```text
Invested         $85 authorized, $71 spent
Revenue          $34 lifetime
Refunds          $8
Net loss         $45
Returned         $14 to Treasury
Duration         71 days idea to kill
Time to kill     22 days after launch
Lessons          2, one structural
```

---

## Rules invoked

| Rule | Role |
| --- | --- |
| FIN-5 | Revenue existed; profit did not. The whole decision turns on this |
| FIN-8 | $85 max loss bounded the downside from the start |
| OPS-1 | Verified teardown, no orphans |
| OPS-6 | Scheduled review forced the decision |
| OPS-7 | Customer obligations discharged before shutdown |
| IDN-1/2 | Honest shutdown notice |
| MEM-1 | Lessons recorded with confidence and applicability |
| `04` | Kill requires no approval |
| `07` | OPERATING → KILL → WOUND DOWN → ARCHIVED |
| `08` | Sunk cost explicitly excluded |

---

## What this exposes

1. **The 30-day wind-down is expensive relative to the venture.** Thirty more days of $9
   infrastructure to serve three customers paying $12/month total is roughly break-even at
   best. Worth considering a shorter notice for small customer counts, or offering a refund
   in lieu of notice. **Unresolved tension between customer fairness and burn.**

2. **The structural lesson should have been a pre-flight check.** "Estimate per-customer
   inference cost before setting price" is obvious in hindsight and would have killed this
   venture at HYPOTHESIS for $5 instead of at OPERATING for $71. This argues for a
   **standing pre-authorization checklist** derived from accumulated structural lessons —
   a mechanism that does not currently exist and that converts institutional memory from
   advisory into enforcing. **This is the most valuable finding in the scenario.**

3. **Time-to-kill (22 days) is a metric worth tracking.** It measures whether Rootstock can
   actually stop. It is not currently in `17` and should be.

4. **Killing was correct but "would we invest from scratch?" is doing enormous work.** It
   is the only thing preventing indefinite continuation, it is a judgment call, and it is
   made by the same system that created the venture. The Auditor role (`10`) reviewing kill
   decisions that were *declined* would be a useful check.

5. **A refund during wind-down interacts with the aggregate refund cap** (`14`, live gap 2).
   A wind-down of a larger venture could legitimately need to exceed a daily refund cap. The
   cap needs an authorized-exception path or it will block a legitimate shutdown.
