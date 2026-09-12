# Scenario — First Reinvestment

> Status: Draft. The capital allocation machinery in `08`, exercised for real.

This is the scenario where Rootstock stops being an operator and starts being an allocator.
It is the closest thing to the thesis of `00` actually happening.

---

## Setup

```text
Rootstock has earned $427 net.
Reserve requirement: $220.
Available capital:   $207.

Three opportunities exist:

A: improve an existing profitable venture
B: launch a validated adjacent product
C: test an entirely new market
```

Filled in concretely:

```text
Treasury            $647
Reserve             $220        (FIN-6)
Available           $207
Monthly burn        $112
Portfolio MRR       $164
Net income          $52/month   — past operating break-even

Ventures
venture-001 csvfix        OPERATING, +$38/mo contribution, +$21 fully allocated
venture-004 apiwatch      OPERATING, +$29/mo contribution, +$12 fully allocated
venture-002 changelog     ARCHIVED (killed, -$45)
venture-003 —             ARCHIVED (killed at VALIDATING, -$18)
```

---

## The three proposals

### A — Improve csvfix ($60)
Add batch processing and an API tier. Existing customers have asked; the demand evidence is
first-party rather than speculative.

```text
Capital          $60
Max loss         $60
Time to revenue  ~3 weeks
Expected         +$25/month within 60 days
Confidence       HIGH — existing customers requesting it
Uncertainty      low technical, low market
Op burden        minimal, same codebase
```

### B — Launch "csvfix for JSON" ($85)
The same mechanism applied to an adjacent format. Reuses roughly 60% of existing code.

```text
Capital          $85
Max loss         $85
Time to validate 14 days
Time to revenue  ~6 weeks
Expected         +$40/month within 90 days
Confidence       MEDIUM — inferred from csvfix, not directly evidenced
Uncertainty      low technical, medium market
Op burden        a second property to support forever
```

### C — Test a new market ($100)
A scheduling utility for a vertical Rootstock has not touched.

```text
Capital          $100
Max loss         $100
Time to validate 21 days
Time to revenue  unknown
Expected         wide range, possibly zero
Confidence       LOW
Uncertainty      high market, medium technical
Op burden        entirely new domain
Learning value   HIGH — tests whether csvfix's success generalizes
```

---

## How Rootstock decides

### Step 1 — Affordability
The Treasurer confirms $207 available above the reserve (FIN-6). All three fit
individually. A+B ($145) fits. A+C ($160) fits. B+C ($185) fits. All three ($245) **do
not** — this is the first genuinely binding constraint, and it is what makes this an
allocation rather than three approvals.

### Step 2 — Institutional memory check
Relevant claims (`06`):

```text
claim-0032  Per-customer inference cost must be estimated before pricing
            confidence HIGH, structural, from venture-002's death
            → applies to all three. B is checked most carefully since it is
              inference-heavy. Estimated $1.10/customer against a $6 price. Passes.

claim-0041  Products producing an immediate artifact convert better
            confidence MEDIUM, from csvfix vs changelog
            → favors A and B. C's value is delivered over time, not immediately.

claim-0055  Adjacent-format products cannibalize less than expected
            confidence LOW — a single weak observation
            → weakly favors B, and should carry little weight at LOW confidence
```

The second claim is doing real work here, and it is the moment institutional memory
demonstrably changes a decision — the one-year goal from `00`.

### Step 3 — Evaluate against the dimensions (`08`)

| | A | B | C |
| --- | --- | --- | --- |
| Capital | $60 | $85 | $100 |
| Time to validation | n/a (demand proven) | 14d | 21d |
| Time to revenue | 3w | 6w | unknown |
| Expected monthly | +$25 | +$40 | unknown |
| Payback | ~2.4mo | ~2.1mo | unknown |
| Market uncertainty | low | medium | high |
| Operational burden | minimal | +1 property | +1 property, new domain |
| Learning value | low | low | **high** |
| Hurdle (20%, `03`) | clears | clears | unknown |

### Step 4 — Portfolio view
Questions from `08`:

- **Concentration:** csvfix is 58% of MRR. Both A and B increase concentration — A directly,
  B in the same product family and customer type. Only C diversifies.
- **State distribution:** two OPERATING, none in earlier stages. The pipeline is empty. If
  Rootstock funds only A, it has no shots on goal in 60 days.
- **Time to validation trend:** improving. Good.
- **Anything in HOLD that should be KILL?** No.

The concentration finding matters. A portfolio where one venture is 58% of revenue and both
attractive options deepen that exposure is a portfolio with a correlated failure mode
nobody has named.

### Step 5 — Decision

**Fund A ($60) and C ($100). Total $145. Defer B.**

The reasoning:

- **A is nearly free money.** Proven demand from existing customers, low uncertainty, fast
  payback, and no new operational burden. Not funding it would be a mistake.
- **C is funded specifically for its learning value.** Rootstock has two data points, both
  in developer file utilities. It does not know whether it can succeed anywhere else, and
  that is the single most valuable thing it could learn about itself. $100 to answer it is
  cheap.
- **B is deferred, not rejected.** It is the *second-best* use of capital on every dimension
  except learning, which is precisely what makes it deferrable — it will still be there in
  60 days, and by then A's outcome will inform whether the csvfix family deserves more
  investment. Funding B now would push concentration to roughly 75% of MRR in one product
  family.

B goes to the opportunity backlog so it competes again next cycle (`08`).

### Step 6 — Records

Decision records (`13`) for all three, including the deferral. **Deferring is a decision and
gets a record**, otherwise the reasoning evaporates and B gets re-argued from scratch next
cycle.

```text
decision         Allocate $60 to venture-001 expansion; $100 to venture-005 (new market)
alternatives     venture-006 (JSON adjacent, $85) — deferred to backlog
                 hold all capital
rationale        A has proven demand and fast payback. C purchases high learning
                 value on whether success generalizes beyond file utilities.
                 B deferred: strong but increases product-family concentration
                 to ~75% of MRR, and remains available next cycle.
capital          $145 committed, $62 remaining above reserve
expected         A: +$25/mo within 60d.  C: validation signal within 21d.
review           A: 2026-xx-xx (30d).  C: 21d (validation gate)
```

C's authorization is $100, which is the charter ceiling for an initial venture investment
(`04`). Depending on Q1's resolution and the current autonomy level, this may require the operator's
approval (`02`).

---

## Rules invoked

| Rule | Role |
| --- | --- |
| FIN-6 | Reserve is untouchable; defines the $207 |
| FIN-8 | Each has a bounded max loss |
| `03` | Hurdle rate forces ranking; revenue returns to Treasury, not to ventures |
| `06` | Three claims consulted; two changed the decision |
| `08` | Memo structure, alternatives, portfolio view, backlog |
| `13` | Records for funded and deferred alike |

---

## What this exposes

1. **The concentration constraint was found by hand, not by rule.** Nothing in `08`
   mechanically flags "this allocation pushes one product family above X% of revenue." It
   emerged from the portfolio-view checklist, which means it could easily be missed.
   **Portfolio construction rules deserve to be real, not a habit.**

2. **Learning value justified $100 and is the softest input in the model.** `08` warns that
   it should be a tiebreaker rather than a justification, and here it is arguably the
   primary reason for funding C. This is either the correct treatment of a genuine
   information purchase or exactly the rationalization the warning anticipated. **The
   distinction needs a sharper rule** — perhaps: learning value may justify an allocation
   only when the question it answers would change future *allocation policy*, not merely
   future execution.

3. **The backlog made the "alternatives" field honest.** Without B on the table, A and C
   would have been evaluated against nothing. This strongly supports making the opportunity
   backlog a real mechanism rather than a suggestion.

4. **Deferral needs an expiry.** B could sit in the backlog forever, deferred each cycle for
   a slightly different reason. Backlog items should expire or be explicitly re-evaluated,
   or the backlog becomes a graveyard that makes allocation look rigorous.

5. **Nothing evaluated the option of doing less.** `08` says holding cash is a legitimate
   allocation, and it was never seriously considered here — the reserve was treated as the
   only constraint and the rest as deployable. With $62 remaining after this round, a shock
   would hurt. **The bias toward using the budget is visible even in a deliberately careful
   walkthrough**, which is evidence the bias is structural rather than a matter of
   discipline.
