# 00 — Vision

> Status: Draft. See `README.md` for status marker conventions.

## The thesis

**Rootstock's unit of output is not code. Its unit of output is a sustainably operated
economic asset.** `[SETTLED]`

This is the load-bearing sentence of the entire project. Everything downstream is a
consequence of it. If Rootstock writes beautiful software that nobody pays for, it has
produced nothing. If Rootstock buys a boring script that earns $12/month forever, it has
produced something real.

A second framing, equally foundational: Rootstock's actual output is **capital allocation
decisions**. The software is a byproduct of deciding where money should go.

## What Rootstock is

An autonomous venture studio. It holds delegated capital and delegated capabilities, and
it runs a continuous loop:

```text
OBSERVE → RESEARCH → IDENTIFY OPPORTUNITY → FORM HYPOTHESIS
   → ESTIMATE (demand, cost, risk, time to revenue)
   → ALLOCATE SMALL CAPITAL → BUILD MVP → DEPLOY → MARKET
   → OPERATE → MEASURE → { INVEST | KILL } → INSTITUTIONAL MEMORY
```

That loop runs indefinitely. Each pass through it should make the next pass slightly
better informed, because the outcome feeds institutional memory (`06`).

The instruction Rootstock receives is not "build me a website." It is:

> Here is capital. Maximize sustainable return subject to this constitution.

## What Rootstock is explicitly not

- **Not an agent framework.** Frameworks provide a way to call tools in a loop. Rootstock
  is an organization with a balance sheet, a constitution, and a portfolio. The agent
  machinery is an implementation detail that could be swapped wholesale.
- **Not a legal owner of anything.** A human-controlled corporation owns the bank account,
  the domains, the AWS organization, and the intellectual property. Rootstock has
  delegated operational authority over those assets and nothing more. `[SETTLED]`
- **Not independent of the operator.** The goal is *operational sovereignty with constitutional
  dependence*, not literal independence. The operator remains the root of trust permanently, by
  design, and this is not a limitation to be engineered away. `[SETTLED]`
- **Not a demo.** Success is measured in months of continuous operation and real money
  from real strangers, not in an impressive transcript.
- **Not a growth-at-all-costs machine.** Rootstock optimizes for sustainable positive cash
  flow and preserved runway, not revenue or headline metrics (`17`).

## Why it exists

The interesting question is no longer "can an AI build an app?" That is answered.

The question is:

> Can an artificial organization learn to allocate scarce capital, discover demand, create
> value, retain institutional knowledge, operate its creations, and compound the proceeds
> over years?

That is a materially harder problem, and it is one where the bottleneck is not model
capability. It is memory, accounting discipline, governance, and the ability to kill
things. Those are organizational problems, and they are what Rootstock is actually about.

## What makes this different from an agent framework

Four things, concretely:

1. **A deterministic ledger.** Rootstock's financial state is not in a context window. It
   is accounting data, and the model reads it rather than remembering it (`03`).
2. **Constraint through economics rather than instruction.** Rootstock is not primarily
   constrained by being told what not to do. It is constrained by a budget it cannot
   exceed and capabilities it does not hold. Freedom inside an economic environment is
   both safer and more interesting than freedom inside an AWS account. `[SETTLED]`
3. **Institutional memory that outlives any single venture.** Lessons compound across
   ventures. In time, the accumulated knowledge may matter more than the accumulated
   capital.
4. **Ventures that can die.** A framework has tasks that succeed or fail. Rootstock has
   assets that must continuously justify their existence or be terminated (`07`).

## What constitutes genuine autonomy

Autonomy here is not binary and not a property of the model. It is a graded property of
each capability, granted explicitly (`02`). Rootstock might hold entrepreneurial autonomy
over deployment while holding no autonomy whatsoever over constitutional change.

The working definition: **Rootstock is autonomous to the degree that value is created
without a human being in the causal path of the decision.** Not without a human in the
loop at all — the operator still reviews, approves large expenditures, and holds a kill switch —
but without a human needing to originate, sequence, or supervise the work.

The honest test is the north-star metric from `17`: **profit generated per human minute of
intervention.** Autonomy increases when that denominator falls while the numerator holds.

## What "self-sustaining" means

Precisely, and in ascending order of difficulty:

1. **Venture break-even.** One property's revenue exceeds its own directly attributable
   costs.
2. **Operating break-even.** Total portfolio revenue exceeds *total* Rootstock costs,
   including shared infrastructure, model inference, and the Workspace bill. This is the
   number that matters, and it is the one most easily faked by ignoring allocated
   overhead (`03`).
3. **Capital recovery.** Cumulative net income exceeds the initial human contribution.
   Rootstock has repaid its founding investment.
4. **Reproduction.** Rootstock funds a new venture entirely from retained earnings, and
   that venture reaches break-even. At this point Rootstock has reproduced productive
   capacity using its own proceeds, which is the threshold where this stops resembling an
   agent demo.

Stage 4 is the real goal. Stages 1 through 3 are prerequisites.

## Where the bootstrap deliberately starts narrower

Not "here is $5,000, go make money" — that makes debugging nearly impossible. Instead:

> **Generate, launch and operate one profitable digital property without human operational
> intervention.**

That is **version 1.0**, and it is reached through a staged ladder (`16`) that adds one
class of capability at a time: an organism that wakes and records (0.0), then research
(0.1), sandbox building (0.2), deployment (0.3), external contact (0.4), bounded spending
(0.5), a first venture (0.6), and finally a stranger's dollar (1.0).

The staging matters as much as the destination. Money does not appear until 0.5, so the
expensive failure modes in `14` cannot fire during the rungs where the system is least
trustworthy.

Initial capital: **$250** `[PROVISIONAL]`, granted at 0.5 rather than at the start. See
`18-open-questions.md`.

Permitted venture types:

- micro-SaaS, paid API, specialized data product, information service, developer utility,
  niche subscription, paid report or database, small B2B tool.

Excluded before 1.0, without exception:

- physical products, hiring, loans, investment or trading, regulated industries, large
  cold-email operations, and any business whose economics require Rootstock to pretend to
  be a human. `[SETTLED]`

That last exclusion is not a compliance checkbox. A business model that only works through
deception is one Rootstock cannot honestly operate, and it would corrupt the experiment's
results even if it worked.

## What success looks like

The first milestone is not `$1M ARR`. It is:

> **A stranger paid Rootstock $1 without the operator touching the transaction.**

That is the moment Rootstock is alive as an economic system. Then:
`$1 → $10 → $100 → operating break-even → initial investment recovered → second venture
funded from earnings.`

### Horizons

**One month.** Rootstock boots, holds a real treasury, produces its first opportunity
theses, and deploys at least one property that a stranger can reach and pay for. Failure
to earn anything is an acceptable outcome; failure to *produce an auditable decision
trail* is not.

**One year.** Several ventures have been launched and most have been killed. Rootstock is
at or near operating break-even. Institutional memory demonstrably changes behavior —
Rootstock declines an opportunity by citing a lesson from a previous failure. Human
intervention is measured in minutes per week rather than hours.

**Five years.** Rootstock has compounded retained earnings across multiple generations of
ventures, has survived at least one serious incident (compromise, vendor ban, or cost
explosion) without human rescue, and holds institutional knowledge that would take a human
operator years to reconstruct. The portfolio, not any individual venture, is the asset.

## The governance shape, in one picture

```text
SEAN / LEGAL ENTITY
        │  constitutional control, root of trust, emergency stop
   ┌────▼─────┐
   │ Rootstock │  Governor
   └────┬─────┘
        │
  ┌─────┼──────┐
Research  Ops  Treasury
        │
  ┌─────┴─────┐
Venture A   Venture B      (isolated AWS account, domain, repo, support each)
```

The model to copy is AWS Organizations: the operator is the management account, Rootstock is an
autonomous member organization. Rootstock can build an empire underneath itself, and there
is still a red button above it. `[SETTLED]`
