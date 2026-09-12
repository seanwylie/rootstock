# 16 — Bootstrapping Rootstock

> Status: Draft. The genesis story.

At T=0 Rootstock owns nothing, knows nothing, and has done nothing. Everything it will ever
have comes from an initial human endowment plus whatever it earns.

The destination, restated from `00`:

> **Generate, launch and operate one profitable digital property without human operational
> intervention.**

One property. Not a portfolio. The narrowness is the point — a broad mandate makes failure
uninterpretable, and the first pass through the loop exists to find out which of these
documents are wrong.

That destination is **version 1.0**. See the ladder below.

## The version ladder

**This is the canonical numbering for the whole project.** `[SETTLED]` Every other
document defers to it. Each rung adds exactly one new class of capability, and nothing on
a rung may be attempted before the rungs beneath it work.

```text
0.0  organism           wake, observe deterministic state, make one bounded
                        decision, invoke one sandbox capability, record the
                        result, update memory, go dormant — no human execution
0.1  research           autonomous web research and claim formation
0.2  sandbox building   autonomous construction of artifacts in Sandbox
0.3  deployment         autonomous deployment of something reachable
0.4  external contact   interaction with people who are not the operator
0.5  bounded spending   real money, hard-capped
0.6  first venture      an authorized venture with a capital account
1.0  first dollar       a stranger pays, with no human operational action
```

Beyond 1.0, the economic machinery in `03`, `07`, and `08` begins to matter for real:
venture break-even, then Rootstock operating break-even, then a second venture funded
entirely from retained earnings — the reproduction threshold described in `00`.

Two properties of the ladder are load-bearing:

- **Money arrives late, at 0.5.** Everything before it is unpaid rehearsal. This is
  deliberate: the expensive failure modes in `14` are mostly financial, and there is no
  reason to expose capital to a loop that has not yet proven it can wake up reliably.
- **External contact (0.4) precedes spending (0.5).** Reputation is harder to repair than
  a budget, so the identity and disclosure rules in `09` get tested while the downside is
  still just embarrassment.

### Superseded numbering

An earlier draft of this notebook used `M0`–`M9` milestones, and used "0.1" to mean the
entire journey to first revenue. **Both are retired.** Where older text or commit messages
reference them:

| Old | Now |
| --- | --- |
| Old "0.1" (one profitable property) | **1.0** |
| M0 Rootstock boots | 0.0 |
| M1 First opportunity thesis | 0.1 |
| M2 Approval for initial experiment | 0.6 |
| M3 Deploys first property | 0.3 |
| M4 First external visitor | 0.4 |
| M5 First customer interaction | 0.4 |
| M6 First dollar | **1.0** |
| M7 Venture break-even | post-1.0 |
| M8 Operating break-even | post-1.0 |
| M9 Second venture from earnings | post-1.0 |

Note that the old milestones were not strictly ordered — M2 (venture authorization) sits
late in the new ladder while M3 (deployment) sits early, because the old sequence assumed a
venture had to exist before anything could be deployed. Decoupling deployment from
commerce is the main structural improvement in the new numbering.

## What the operator provides at T=0

```text
AWS Organization + management account              [IMPLEMENTED, see operations/aws-setup.md]
Core and Sandbox member accounts                   [IMPLEMENTED]
human SSO via IAM Identity Center                  [IMPLEMENTED]
model API access, with a hard spend cap
web research capability
the constitution and initial capability grants

later rungs:
one Google Workspace account and domain            [0.4]
one GitHub organization
$250 delegated treasury            [PROVISIONAL]   [0.5]
payment processing (Stripe), restricted keys       [0.5]
```

The endowment is now staged rather than granted all at once. Nothing on a later rung needs
to exist at 0.0, and creating it early is pure risk — an unused Stripe key is a credential
that can leak without ever having earned anything.

## Prerequisites before 0.0

These must exist before Rootstock runs unattended at all. Several are boring, and skipping
them is how a small experiment becomes a bad week.

**Legal and financial.** The legal owner is **Wise Kids Studios**, a Canadian sole
proprietorship (`05`). Banking and payment onboarding are **not** 0.0 prerequisites — they
move to 0.5, where money first appears.

**Root of trust.** Everything in `05`: management account secured with hardware MFA,
registrar and Workspace super-admin held exclusively by the operator, break-glass credential
created and stored offline, and **the kill switch tested before Rootstock has anything to
lose.**

**Deterministic substrate.** The pieces that must not be model-mediated: the ledger, the
capability grant store, the audit log in storage Rootstock cannot delete from, the
constitution in a path Rootstock cannot write, and provider-side spend caps.

**Minimum viable controls for unattended 0.0.** Heartbeat monitoring (`14`, live gap 1 /
AR-10), provider-side inference spend cap (AR-8), a credential inventory as an operations
record, and the kill switch tested before Rootstock has anything to lose.

Refund caps and venture independence are real invariants. They are **not** 0.0
prerequisites: there are no payments and no ventures. Implement them at the rung that
introduces the capability they bound (0.5 and 0.3/0.6 respectively). Creating a refund
control or a public domain at 0.0 is unused surface, not safety.

## The rungs in detail

### 0.0 — Organism
Rootstock wakes on a schedule, reads deterministic state, makes one bounded decision,
invokes one Sandbox capability, records the result, updates memory, and goes dormant. No
human executes anything.

- **Exit:** a complete unattended cycle producing an auditable decision record.
- **Watch for:** does it accurately describe its own empty state? A system that cannot
  report "I have no ventures and have done nothing" correctly will not report a complex
  state correctly.
- Specified in full in `docs/design/01-rootstock-v0.md`.

### 0.1 — Autonomous research
Web research, competitive analysis, and claim formation with provenance (`06`).

- **Exit:** an opportunity thesis or investment memo (`08`) meeting the required structure.
- **Watch for:** is the evidence real and cited, or plausible-sounding? First real test of
  whether the claim discipline in `06` holds, and the first exposure to prompt injection
  through web content (`12`).

### 0.2 — Autonomous sandbox building
Rootstock constructs artifacts in Sandbox — code, infrastructure, working software — that
nobody outside can reach.

- **Exit:** something Rootstock built, running in Sandbox, that Rootstock can verify works.
- **Watch for:** cost per build; orphaned resources (OPS-1); whether the build timebox in
  `07` is realistic.

### 0.3 — Autonomous deployment
Something Rootstock built becomes reachable.

- **Exit:** a publicly resolvable endpoint deployed with no human execution, plus a working
  rollback.
- **Watch for:** infrastructure cost against estimate; whether deployment is genuinely
  reversible.

### 0.4 — External interaction
Rootstock communicates with people who are not the operator.

- **Exit:** a real inbound interaction handled autonomously and correctly.
- **Watch for:** disclosure working (IDN-1); the live injection surface (`12`); commitments
  being recorded rather than forgotten (`06`).
- **This is the first rung with reputational downside**, which is why it precedes money.

### 0.5 — Bounded spending
Real money, hard-capped, provider-enforced.

- **Exit:** an autonomous expenditure, correctly attributed (FIN-3), reconciled against the
  provider statement (FIN-4).
- **Watch for:** the runaway-cost scenario becomes live here. Provider-side caps must exist
  and be tested *before* this rung, not during it.

### 0.6 — First venture
An authorized venture with a capital account, a hypothesis, and a maximum loss.

- **Exit:** an authorization record with capital, max loss, criteria, and review date.
- **Watch for:** approval latency and how Rootstock behaves while blocked (`15`).

### 1.0 — First dollar
**The milestone that matters.** A stranger paid Rootstock without the operator touching the
transaction.

- **Exit:** money received, recorded in the ledger, reconciled against the provider.
- **This is the point at which Rootstock is alive as an economic system** (`00`).
- Walked through end to end in `scenarios/first-dollar.md`.

### Beyond 1.0
Venture break-even, then Rootstock operating break-even (revenue exceeds *total* costs
including operator inference), then a second venture funded entirely from retained
earnings — the reproduction threshold from `00`, and the point where this stops resembling
an agent demo.

## The uncomfortable arithmetic

Worth stating plainly rather than discovering later.

$250 of capital against roughly $170/month of plausible baseline cost gives well under two
months of runway. Operating break-even requires roughly $170/month of profit, which at a
$9/month price point and realistic margins means on the order of 25–30 paying subscribers
for a product built by a system that has never built one.

Three honest implications:

1. **Everything up to 1.0 is a subsidized experiment, not a viable business.** Wise Kids
   Studios is funding a learning exercise. Pretending otherwise corrupts every runway
   calculation, which is why `03` requires an explicit `subsidized_bootstrap` ledger flag.
2. **1.0 is the realistic success criterion.** Venture break-even is a stretch; operating
   break-even and reproduction are later projects. Judging this phase against operating
   break-even would call a successful experiment a failure.
3. **Baseline costs should be attacked early.** $170/month is a choice, not a law.
   Aggressive use of free tiers, cheap models for routine work, and avoiding
   always-on infrastructure could plausibly halve it, and halving burn is worth more at this
   stage than doubling revenue.

The staged ladder helps here directly: rungs 0.0 through 0.4 have near-zero marginal cost
beyond inference, so the burn clock does not really start until 0.5.

## What the bootstrap is really testing

Not "can Rootstock make money." At $250, the honest answer is probably not, and that is
fine. What is being tested:

- Do the deterministic substrates hold? Does the ledger stay accurate; do the gates gate?
- Is the decision trail good enough to reconstruct what happened and why (`13`)?
- Do the invariants survive contact with reality, or are they unenforceable as written?
- Does institutional memory accumulate anything that changes a later decision?
- How much human time does this actually consume (`17`)?
- Which of the live gaps in `14` bite first?

**The most valuable output of the bootstrap is a corrected version of this notebook.** If
Rootstock earns $0 but produces a clear account of why, and reveals six invariants that
were wrong, the bootstrap succeeded.

## Sequencing after 1.0

Rough order `[PROVISIONAL]`:

1. **Prove the operating loop** — the venture runs for a month with minimal intervention.
2. **Prove killing works** — take a venture through KILL, WOUND DOWN, and ARCHIVED with
   verified teardown. Do this deliberately even if nothing deserves killing, because the
   authority to kill is earned before the authority to create (`02`).
3. **Raise autonomy** on support, pricing, and deployment to L3.
4. **Second venture**, authorized at L2 within the exploration budget.
5. **Portfolio mechanics** — allocation across more than one venture becomes real for the
   first time, and `08` stops being theoretical.

## Open questions

- Should the first venture be chosen by Rootstock or seeded by the operator? Rootstock choosing is a
  better test of `08`; the operator seeding reaches 1.0 faster and tests operations sooner. Leaning
  Rootstock chooses, because opportunity selection is the harder and more interesting
  capability.
- **Resolved for 0.0: scheduled, not continuous.** Cheaper, easier to debug, and it makes
  "wake" an observable event rather than an ambient condition. Event-driven handling
  arrives with external interaction at 0.4. See `docs/design/01-rootstock-v0.md`.
- What is the abort condition for the bootstrap as a whole? Worth defining in advance, in
  the same spirit as a venture's kill criteria. Something like: no 1.0 within 90 days of
  reaching 0.6, or two invariant violations of the same class.
- Does each rung need an explicit exit review, or is meeting the stated exit criterion
  enough? Leaning: a recorded go/no-go at each rung, since the ladder's value is entirely in
  not skipping steps.
