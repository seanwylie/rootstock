# 08 — Capital Allocation

> Status: Draft. Where Rootstock becomes a genuinely autonomous economic actor.

Capital allocation is Rootstock's actual product. Everything else — the code, the
deployments, the support responses — is the mechanism by which allocation decisions get
expressed. A Rootstock that writes excellent software and allocates badly is a failure. A
Rootstock that writes mediocre software and allocates well will compound.

The core discipline: **every venture must continuously compete with every alternative use
of the same dollar**, including the alternative of holding it.

## The investment memo

Every capital request produces one. It is the artifact that makes allocation auditable and
comparable, and it is required at AUTHORIZED and at every follow-on (`07`).

```text
VENTURE            venture-004 / working name
DATE               2026-03-14
REQUEST            $85 initial

HYPOTHESIS
We believe [specific user] will pay [amount] for [outcome]
because [evidence].

EVIDENCE
- [cited observation, with source and date]
- [relevant institutional claims, with ids and confidence]
- [what we do NOT know]

CAPITAL REQUESTED  $85
MAXIMUM LOSS       $85          (hard ceiling, FIN-8)
BURN RATE          ~$12/month projected

VALIDATION
Signal             40 email signups OR 5 pre-orders
Period             14 days
Cost to validate   $15

SUCCESS CRITERIA   $50 MRR within 90 days of launch
FAILURE CRITERIA   No validation signal in 14 days
                   No revenue within 60 days of launch
                   Contribution margin negative at day 90

FOLLOW-ON RULE     Additional capital only on:
                   positive contribution margin AND payback < 6 months

REVIEW             Weekly until first revenue, then monthly

RISKS
Market             [uncertainty]
Technical          [uncertainty]
Legal              [uncertainty]
Operational        [ongoing burden this creates]

ALTERNATIVES
What else could this $85 do?
[explicit comparison to at least one other option]
```

Two fields do most of the work.

**Maximum loss** converts an open-ended bet into a bounded one, and it is enforced
mechanically rather than by judgment (FIN-8). When cumulative spend hits it, the venture
stops. No appeal, no "just a bit more."

**Alternatives** is the field that makes this allocation rather than approval. A proposal
evaluated in isolation is nearly always approvable — it has upside, the amount is small,
the reasoning is sound. The comparison is what forces ranking.

## Evaluation dimensions

Considered for every proposal:

```text
expected upside          how big if it works
capital required         how much to find out
time to validation       how fast we learn
time to revenue          how fast it pays
market uncertainty       do we know demand exists
technical uncertainty    can we actually build it
legal risk               regulatory or contractual exposure
operational burden       ongoing attention forever after
competitive moat         can it be trivially copied
reuse potential          does it build shared capability
learning value           what we learn even if it fails
```

Three of these are chronically underweighted by anyone — human or model — evaluating their
own idea:

- **Operational burden.** A venture earning $15/month that generates weekly support tickets
  is a net negative. Every launched venture is a permanent liability on attention until
  archived, and that cost never appears in a P&L.
- **Time to validation.** Fast-failing options are worth more than their expected value
  suggests, because they return capital *and* information quickly. A 14-day validation at
  $20 dominates a 90-day validation at $20 even at identical odds.
- **Learning value.** A failure that resolves a recurring uncertainty is partly an
  investment in institutional memory (`06`). This is real but easily used to rationalize
  anything — it should be a tiebreaker, never a justification.

`[OPEN]` — should these be formally scored and weighted, producing a rankable number? A
score is comparable and auditable but invites gaming and false precision at nine data
points. Leaning: structured qualitative assessment during bootstrap, with scoring revisited once
there are enough completed ventures to calibrate against.

## Allocation rules

`[PROVISIONAL]` throughout.

1. **Reserve first.** No allocation may breach the reserve requirement (FIN-6). The reserve
   is not a soft target.
2. **Initial venture investment ≤ $100** (charter, `04`).
3. **Concurrent active experiments ≤ 3** — attention is the scarce resource, not money.
4. **Exploration budget is capped per period** so that a run of appealing ideas cannot
   consume the treasury.
5. **Follow-on requires evidence**, never enthusiasm. The follow-on rule was pre-registered
   in the memo; it is checked, not renegotiated.
6. **Follow-on must clear the hurdle rate** (`03`) — 20% annualized, existing purely to
   force ranking.
7. **Capital returns to the Treasury**, never to the venture that earned it (`03`). Every
   dollar re-competes.
8. **No cross-venture lending** (FIN-2 applies internally too).

## Follow-on discipline

Follow-on decisions are where portfolio returns are actually determined, and where the
strongest cognitive pull toward error exists.

The rule: **evaluate a follow-on as if it were a new investment in a company you do not
already own.** Given today's evidence, at today's price, with no history — would this be
the best use of the capital?

Explicitly excluded from consideration:
- How much has already been invested (sunk)
- How much work went into it
- That killing it would look like failure
- That it is *almost* working

Explicitly included:
- Current unit economics from the ledger, not projections
- Whether the original hypothesis was validated or quietly redefined
- What the same capital would do elsewhere
- The operational burden added by scaling it

**Hypothesis drift is the specific thing to watch for.** A venture that launched to prove
"developers will pay for X" and is now earning small amounts from something adjacent has
not validated its hypothesis. It may still be worth funding — but as a *new* hypothesis
with a new memo, not as a follow-on. Otherwise the memo becomes retrospective narrative.

## The portfolio view

Rootstock allocates across the portfolio, not to ventures one at a time. Portfolio-level
questions at each allocation cycle:

- What is the total capital at risk right now, and is that appropriate given runway?
- Is the portfolio concentrated in one market, one channel, or one vendor? Correlated
  failure is invisible until it isn't.
- How many ventures are in each state (`07`)? Too many in BUILDING means Rootstock is
  producing rather than validating.
- What is the median time to validation, and is it improving? This is the real measure of
  whether Rootstock is learning (`17`).
- Is anything in HOLD that should be in KILL?

`[OPEN]` — should there be a deliberate portfolio shape, such as "at most one high-effort
venture at a time, alongside two cheap experiments"? Real venture portfolios have
construction rules. At three concurrent ventures the question may be premature, but the
habit is worth forming early.

## Deciding to hold cash

An underrated option. Holding capital is a legitimate allocation, and Rootstock should be
able to conclude "none of these are good enough" without that reading as failure.

Cash should be preferred when: no proposal clears the hurdle, runway is thin, an existing
venture needs attention more than a new one needs capital, or a recent failure suggests
waiting for the lesson to be understood before deploying again.

The bias to guard against is the opposite: an autonomous system with a budget and a mandate
will tend to *use* the budget. Structurally, doing nothing must be as easy as doing
something, and it should be recorded as a real decision (`13`) rather than as inaction.

## Decision record

Every allocation, including refusals and decisions to hold, produces a record per `13`:

```text
Decision      Allocate $85 to venture-004
Alternatives  venture-002 follow-on ($85), hold
Rationale     [why this one]
Evidence      [memo id, ledger figures, claim ids]
Authority     capital-allocation-L1 (the operator approved 2026-03-14)
Capital       $85 committed, $85 maximum loss
Expected      validation signal within 14 days
Review        2026-03-28
```

The `Expected` field is what makes retrospective calibration possible. Comparing expected to
actual across many decisions is how Rootstock finds out whether its judgment is any good —
which is a question the system should be able to answer about itself with data, not
impression.

## Open questions

- Is a hurdle rate meaningful at $250 of capital, or is attention the true scarce resource
  and therefore the right denominator? Flagged in `03` too.
- Should Rootstock maintain an explicit "opportunity backlog" of researched-but-unfunded
  ideas, so that new proposals compete against a real bench rather than against nothing?
  Leaning strongly yes — it makes the alternatives field honest.
- How should allocation handle a venture that is profitable but declining? Harvesting is a
  legitimate strategy and the current model has no vocabulary for it.
- Who decides when Rootstock and the operator disagree about a follow-on? Currently the operator, by `04`.
  Worth recording both views so the calibration data survives the disagreement.
