# 03 — Economic Model

> Status: Draft. Defines Rootstock as an economic system.

The economic model is the primary feedback loop. Not the agent loop, not the deployment
pipeline — the P&L. Everything Rootstock does is ultimately scored here, and the quality of
this model determines whether Rootstock's decisions mean anything.

The founding constraint, restated: **financial state is deterministic accounting data, not
model memory** (FIN-4). The model reads the ledger. The ledger never reads the model.

## Ownership and the capital fiction

Rootstock does not own money. The structure is:

```text
Wise Kids Studios (human-controlled legal owner)
    owns → bank account, Stripe/PayPal, domains, AWS org, IP
    allocates ↓
Rootstock Treasury (delegated capital)
```

The correct phrasing is never "Rootstock owns $14,382." It is "Rootstock Treasury has
$14,382 of capital allocated to it by Wise Kids Studios." `[SETTLED]`

This is not pedantry. It is what makes an emergency stop possible without destroying the
experiment: capital can be withdrawn from the delegated treasury without unwinding
anything legal, and Rootstock's books remain coherent afterward.

## Treasury structure

```text
Rootstock Treasury
    ├── Operating Reserve          (runway floor, untouchable — FIN-6)
    ├── Shared Infrastructure Budget (Workspace, base AWS, inference, tooling)
    ├── Exploration Budget         (new venture experiments)
    │
    ├── Venture A Capital Account
    ├── Venture B Capital Account
    └── Venture C Capital Account
```

Rules governing the structure `[PROVISIONAL]`:

- **The Operating Reserve is not spendable.** It is a floor, not a fund. Breaching it
  triggers restricted mode.
- **Venture capital accounts are ring-fenced.** Venture A's budget cannot be spent on
  Venture B without an explicit reallocation decision, which is a capital allocation event
  (`08`) and gets a decision record (`13`).
- **A venture account can go to zero but never negative** (FIN-1, FIN-8). At zero, the
  venture's spending capabilities are suspended pending a follow-on decision.
- **Revenue flows to the Treasury, not to the venture that earned it.** Ventures do not
  accumulate their own retained earnings and self-fund. All reinvestment is an explicit
  allocation decision, so that every dollar competes against every alternative. This is the
  mechanism that makes `08` meaningful — without it, a mediocre profitable venture would
  quietly absorb its own cash flow forever.

## Chart of accounts

Deliberately small. A chart of accounts that is too detailed will not survive contact with
an autonomous operator, and misclassification is a real failure mode (`14`).

**Assets:** cash by instrument, prepaid balances (domains, annual subscriptions),
receivables from payment processors in transit.

**Liabilities:** should be permanently near-zero under FIN-2. The legitimate cases are
deferred revenue (an annual subscription collected but not yet earned) and refund
obligations. Both matter: deferred revenue counted as profit is a classic way to believe
you are solvent when you are not.

**Equity:** contributed capital (from the legal owner), retained earnings.

**Revenue:** subscription, one-time, usage-based, other. Recognized when earned, not when
collected `[PROVISIONAL]` — accrual matters here specifically because of annual plans.

**Costs**, in five classes, because the distinction drives decisions:

| Class | Examples | Behavior |
| --- | --- | --- |
| **COGS / variable** | Per-transaction payment fees, per-customer API calls, per-request inference | Scales with usage |
| **Venture infrastructure** | That venture's hosting, database, domain, monitoring | Fixed per venture |
| **Model inference** | Agent tokens for building and operating | Split: venture-attributed vs. shared |
| **Customer acquisition** | Ads, listings, paid placement | Discretionary, attributable |
| **Shared infrastructure** | Workspace, base AWS, tooling, Rootstock's own inference | Allocated across ventures |

**Model inference deserves special attention.** It is Rootstock's largest controllable cost
and the one most likely to be quietly excluded from unit economics. It must be attributed:
tokens spent building Venture A are Venture A's capitalized cost; tokens spent answering
Venture A's support tickets are Venture A's operating cost; tokens spent on portfolio-level
research are shared. Unattributed inference violates FIN-3.

## Cost allocation

Shared costs must land somewhere, or every venture looks profitable and the portfolio
loses money — the exact failure FIN-5 exists to prevent.

Allocation method `[PROVISIONAL]`: **equal split across active ventures**, recomputed
monthly. It is crude but has two virtues — it is deterministic and it cannot be gamed by a
venture manipulating a usage metric. Revenue-weighted allocation punishes success;
usage-weighted allocation invites metric-gaming.

The consequence is intentional: a fourth venture reduces the overhead burden on the other
three. Adding ventures has an accounting benefit that partly offsets the attention cost.

**Two figures are reported for every venture, always:**

- **Contribution margin** — revenue minus directly attributable costs. Answers: *does this
  thing pay for itself?*
- **Fully allocated profit** — contribution margin minus allocated shared costs. Answers:
  *does this thing deserve to exist in the portfolio?*

Kill decisions use fully allocated profit. Optimization decisions use contribution margin.
Reporting only one of them is how a portfolio quietly bleeds.

## The venture P&L

Every property carries a scorecard of this shape:

| Metric | Value |
| --- | ---: |
| Invested capital | $84 |
| Monthly revenue | $39 |
| Monthly variable cost | $5 |
| Monthly infrastructure | $3 |
| AI inference | $6 |
| Acquisition | $8 |
| **Contribution margin** | **$17** |
| Allocated shared cost | $9 |
| **Fully allocated profit** | **$8** |
| Lifetime revenue | $143 |
| ROI | 70% |
| Payback period | 5 months |
| **Status** | **INVEST** |

Status is one of **KILL / MAINTAIN / OPTIMIZE / INVEST / EXPAND**, and it is recomputed on
the venture's review schedule (OPS-6). The status is a *proposal* produced by deterministic
rules from ledger data; changing it is a decision requiring a record (`13`).

## Unit economics that must be defined per venture

Before a venture launches, these need definitions, even if the values are guesses:

- **CAC** — fully loaded cost to acquire a paying customer, including the inference spent
  producing marketing material.
- **LTV** — expected gross margin over the customer's life. Requires a churn assumption,
  which will initially be wrong; record it as a claim with confidence (MEM-1) and revise.
- **Payback period** — months to recover CAC. For ventures this small, payback matters more
  than LTV/CAC ratio, because a 14-month payback is indistinguishable from a loss when the
  venture may not survive 14 months.
- **Gross margin per unit.**
- **Break-even volume.**

## Internal cost of capital

Rootstock's capital is scarce, so it should not be free. `[PROVISIONAL]`

Proposal: an internal hurdle rate of **20% annualized** on committed venture capital.
Follow-on investment must project a return above the hurdle to be approved. The rate has no
cash effect — no venture pays interest — it exists purely to force ranking.

The purpose is to make this conversation happen: if Venture A requests another $500, it
must justify why that capital is better placed there than in Venture B or a new experiment.
Without a hurdle, every positive-return request looks approvable and capital drifts toward
whatever asks loudest. See `08`.

`[OPEN]` — is a hurdle rate the right instrument at $250 of total capital, or is it
premature machinery? At this scale, the binding constraint is more likely attention than
capital. Possibly the hurdle should be denominated in *operator attention* rather than
percent.

## Runway and reserve

- **Monthly burn** = shared infrastructure + sum of venture fixed costs + baseline
  inference. Excludes discretionary acquisition spend, which can be halted instantly.
- **Runway** = (Treasury − Operating Reserve) ÷ monthly burn, net of revenue.
- **Reserve requirement** = 6 months of projected burn `[PROVISIONAL]`, per FIN-6.

At $250 of starting capital with roughly $170/month of plausible baseline cost, a literal
six-month reserve is mathematically impossible.

**Resolved `[SETTLED]`: bootstrap-phase exemption.** The reserve requirement in FIN-6
activates only once Rootstock reaches operating break-even. Before that, Wise Kids Studios is
explicitly subsidizing an experiment and the runway concept does not meaningfully apply.

Two conditions attach to the exemption, and they matter more than the exemption itself:

- **The ledger carries an explicit `subsidized_bootstrap` flag while the exemption is
  active.** Rootstock must never report a runway figure that implies solvency it does not
  have. A system that believes it has six months of runway because the check is disabled is
  worse than one with no check at all.
- **The exemption is one-way.** Once Rootstock reaches operating break-even and FIN-6
  activates, it does not revert to exempt if performance later declines. At that point a
  runway breach means restricted mode, as intended.

During the exemption, the substitute control is the absolute treasury balance and the
provider-side spend caps (`11`), not a computed runway.

## The self-sustaining threshold

The moment worth designing toward:

```text
Property A     +$42
Property B     -$11
Property C     +$86
Property D      +$8
Property E    +$119
-------------------
Revenue        $255
Costs          $170
Net             $85
```

Rootstock saves $50 and allocates $35 to Experiment F. Experiment F eventually earns
$70/month. At that point Rootstock has reproduced productive capacity from retained
earnings, which is the threshold described in `00`.

Note Property B: it is losing money and still in the portfolio. That is acceptable only if
there is a recorded decision with a review date explaining why (OPS-6). Tolerated losses
must be deliberate, not residual.

## Accounting discipline

- **Reconcile against external reality on a schedule.** The internal ledger is compared to
  bank, Stripe, PayPal, and cloud billing. Divergence beyond a small threshold is an
  EMERGENCY (FIN-4), because a ledger that has silently drifted invalidates every decision
  made since.
- **Cloud costs lag.** AWS billing is delayed and estimates are imperfect. Accrue estimated
  spend daily and true up when actuals land; never treat "no bill yet" as "no cost."
- **Correct by appending** (MEM-2). Never edit history.
- **Every transaction carries an attribution** (FIN-3) and a link to the causing decision
  where one exists.

## Open questions

- Can one venture lend capital to another? Currently no — it is debt (FIN-2), even
  internally, and it obscures which venture actually earned its keep.
- Can a venture be sold? What happens to the proceeds, and how is a sale price even
  determined for a $40/month property? Tracked in `18`.
- When does internally built tooling become a capitalized asset rather than an expense? At
  this scale, expensing everything is almost certainly correct, but the question returns if
  Rootstock builds a component reused across five ventures.
- How is deferred revenue handled if a venture is killed with active annual subscribers?
  This is a real obligation and it constrains the freedom to kill (OPS-7). Probably: a
  venture with outstanding prepaid obligations cannot be killed, only wound down with
  refunds funded from the reserve.
