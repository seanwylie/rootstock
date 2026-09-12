I’d treat `docs/brainstorm/` as the **conceptual constitution and design notebook for Rootstock**, not implementation documentation yet.

The goal is to capture the things we do *not* want to rediscover six months from now: what Rootstock is, what it is allowed to optimize for, what must remain deterministic, what authority it can earn, how money flows, how ventures live and die, and where human control remains absolute.

I’d start with something like:

```text
docs/
└── brainstorm/
    ├── README.md
    ├── 00-vision.md
    ├── 01-system-invariants.md
    ├── 02-autonomy-model.md
    ├── 03-economic-model.md
    ├── 04-governance-and-authority.md
    ├── 05-root-of-trust.md
    ├── 06-memory-and-institutional-learning.md
    ├── 07-venture-lifecycle.md
    ├── 08-capital-allocation.md
    ├── 09-identity-and-external-presence.md
    ├── 10-agent-organization.md
    ├── 11-tools-and-capabilities.md
    ├── 12-security-and-containment.md
    ├── 13-observability-and-audit.md
    ├── 14-failure-modes.md
    ├── 15-human-intervention-model.md
    ├── 16-bootstrapping-rootstock.md
    ├── 17-success-metrics.md
    ├── 18-open-questions.md
    └── scenarios/
        ├── first-dollar.md
        ├── first-failed-venture.md
        ├── first-reinvestment.md
        ├── customer-support-incident.md
        ├── runaway-cost.md
        └── compromised-capability.md
```

I’d make each document answer a different class of question.

### `README.md`

This should orient anyone opening the directory.

Something like:

> Rootstock is an autonomous venture operating system. It receives bounded capital and capabilities, identifies commercial opportunities, creates and operates digital properties, learns from their outcomes, and reinvests retained earnings into further productive activity.

Then explicitly state:

* these documents are exploratory
* contradictions are allowed for now
* implementation decisions belong elsewhere later
* invariants should eventually graduate into formal specifications/tests

That separation will save a lot of confusion.

---

## `00-vision.md`

The “what are we actually building?” document.

Questions:

* What is Rootstock?
* What is it explicitly *not*?
* Why does it exist?
* What makes this different from an agent framework?
* What constitutes genuine autonomy?
* What does “self-sustaining” mean?
* What does success look like after one month, one year, five years?

I’d capture the core thesis:

> Rootstock's unit of output is not code. Its unit of output is a sustainably operated economic asset.

That's worth making foundational.

---

# `01-system-invariants.md`

Probably the most important file.

These are things that should remain true regardless of architecture.

Examples:

### Financial invariants

* Rootstock may never spend money it does not control.
* Rootstock may never incur debt.
* Every expenditure must be attributable to a venture, shared infrastructure, or explicitly authorized exploration.
* Financial balances come from deterministic ledgers, never model memory.
* Revenue is not profit.
* Rootstock must preserve minimum runway.
* Capital allocation limits cannot be modified by Rootstock itself.

### Control invariants

* A human-controlled root of trust always exists.
* Rootstock cannot remove or weaken the root of trust.
* Rootstock cannot modify its own constitutional constraints.
* Privilege escalation requires external authorization.
* Emergency shutdown must not depend on Rootstock cooperating.

### Identity invariants

* Rootstock does not misrepresent itself as a human.
* Rootstock does not fabricate credentials, testimonials, customers, affiliations, or identities.
* Communications must be attributable to an authorized Rootstock identity.

### Operational invariants

* Every externally visible property has an owner.
* Every capability has an explicit scope.
* Every consequential action is auditable.
* Every venture can be independently disabled.
* Experimental ventures have bounded downside.

Eventually many of these should become assertions in code.

---

# `02-autonomy-model.md`

Define what we mean by autonomous.

I would explicitly avoid binary thinking.

Use levels:

```text
L0 — advisory
Rootstock recommends actions.

L1 — delegated execution
Rootstock performs specifically approved tasks.

L2 — bounded autonomy
Rootstock can act freely within a defined budget/capability envelope.

L3 — operational autonomy
Rootstock independently manages an existing venture.

L4 — entrepreneurial autonomy
Rootstock can discover, fund, build and launch ventures.

L5 — portfolio autonomy
Rootstock allocates capital across multiple ventures and retires poor performers.
```

Then different capabilities can have different levels.

For example:

```text
Deploy code                L4
Reply to support           L3
Spend <$25                 L3
Spend $25–$100             L2
Register approved TLD      L3
Change constitutional rule L0
Borrow money               prohibited
```

This becomes a fantastic way to reason about permissions.

---

# `03-economic-model.md`

Define Rootstock as an economic system.

Include:

* capital
* revenue
* COGS
* infrastructure
* model inference
* customer acquisition
* shared costs
* venture-specific costs
* contribution margin
* operating profit
* retained earnings
* reserves
* reinvestment

And define accounting boundaries.

For instance:

```text
Rootstock Treasury
    |
    +-- Operating Reserve
    +-- Shared Infrastructure Budget
    +-- Exploration Budget
    |
    +-- Venture A Capital Account
    +-- Venture B Capital Account
    +-- Venture C Capital Account
```

I’d also explore whether internal capital carries a hurdle rate.

If Venture A asks for another $500, it should have to justify why that capital is better allocated there than to Venture B or a new experiment.

That's where Rootstock gets interesting.

---

# `04-governance-and-authority.md`

This is effectively the constitution.

Define:

* what Rootstock can decide itself
* what requires approval
* what is permanently prohibited
* what authority can be earned
* what authority can be revoked
* budget limits
* contractual limits
* communications authority
* hiring/service procurement authority
* regulatory boundaries

I'd distinguish:

```text
constitutional authority
operating authority
venture authority
temporary delegated authority
```

Rootstock should be able to grant its child agents less authority than Rootstock itself possesses, but never more.

Capability monotonicity downward.

Very useful invariant.

---

# `05-root-of-trust.md`

This deserves its own treatment.

Questions:

* What belongs exclusively to you/the holding entity?
* Which credentials can Rootstock never access?
* Where does AWS Organizations fit?
* Where do Stripe/PayPal/bank controls live?
* Who owns DNS?
* Who owns Rootstock's identity?
* How do you kill it?
* How do you restore it?
* What if Rootstock accidentally locks itself out?

I'd envision:

```text
Human Root
   |
   +-- Legal ownership
   +-- Master treasury
   +-- AWS Organization management
   +-- Domain registrar root
   +-- Workspace super-admin
   +-- Emergency shutdown
   |
Rootstock
   |
   +-- delegated treasury
   +-- member AWS accounts
   +-- operational Workspace identity
   +-- GitHub org
```

---

# `06-memory-and-institutional-learning.md`

This deserves serious thought because Rootstock's **compounding knowledge may eventually matter more than its capital**.

Break memory into:

* constitutional memory
* identity
* episodic history
* venture state
* relationship/customer state
* reusable knowledge
* hypotheses
* failed experiments
* market observations
* financial records
* source documents

And critically:

### What can be forgotten?

Some memory should decay.

If Rootstock once learned:

> Google Ads CAC for this niche is $47.

that should not become eternal truth.

Store:

```text
claim
evidence
timestamp
confidence
applicability
last validated
```

Institutional memory should behave more like a knowledge base than autobiographical embeddings.

---

# `07-venture-lifecycle.md`

Define what a Rootstock venture *is*.

Possible states:

```text
IDEA
↓
RESEARCH
↓
HYPOTHESIS
↓
AUTHORIZED
↓
VALIDATING
↓
BUILDING
↓
LAUNCHED
↓
OPERATING
↓
──────────────────────────
│        │        │
GROW    HOLD     KILL
│
SCALE
```

For each state, define:

* required evidence
* maximum capital exposure
* allowed capabilities
* exit criteria
* artifacts produced

A venture shouldn't just remain alive because Rootstock forgot about it.

Every venture should have an explicit review schedule.

---

# `08-capital-allocation.md`

This is where Rootstock starts becoming a genuinely autonomous economic actor.

Brainstorm how it evaluates investments:

```text
expected upside
capital required
time to validation
time to revenue
market uncertainty
technical uncertainty
legal risk
operational burden
competitive moat
reuse potential
learning value
```

You could eventually create a Rootstock equivalent of an investment committee memo.

Each proposed venture gets:

```text
Hypothesis
Evidence
Capital requested
Maximum loss
Expected validation period
Success criteria
Failure criteria
Follow-on investment rule
```

Rootstock then has to compete with its own portfolio for capital.

---

# `09-identity-and-external-presence.md`

Very interesting territory.

Rootstock may eventually have:

* a name
* an email address
* websites
* support identity
* social accounts
* published documentation
* invoices
* terms
* customer conversations

Questions:

* Does Rootstock speak as “I”?
* Does each venture have its own identity?
* Is Rootstock visible behind ventures?
* Should customers know the business is autonomously operated?
* When does something get escalated to a human?
* Can Rootstock sign its own emails?
* What claims may it make about itself?

I would strongly favor explicitness:

> “Rootstock Support — automated operations”

rather than pretending there's a person called Amanda in customer service.

---

# `10-agent-organization.md`

This is your synthetic company design.

Don't lock into specific agents yet.

Explore functions:

```text
Governor
Treasurer
Research
Product
Engineering
Design
Growth
Support
Operations
Security
Auditor
```

Important distinction:

These may not be persistent agents.

They could simply be **roles invoked when necessary**.

Rootstock itself should probably be the persistent organizational identity.

---

# `11-tools-and-capabilities.md`

Inventory capability classes rather than vendors.

For example:

```text
COMMUNICATION
- email
- SMS
- support ticketing

COMPUTE
- provision infrastructure
- deploy
- inspect logs
- modify configuration

COMMERCE
- receive payment
- refund
- create subscription
- inspect transactions

IDENTITY
- domains
- DNS
- OAuth
- workspace accounts

RESEARCH
- web
- analytics
- competitive research

DEVELOPMENT
- repositories
- CI/CD
- issue tracking
```

For each capability:

```text
scope
risk class
cost model
credential type
approval model
auditability
revocability
```

This will later map naturally onto Argus-style capability enforcement.

---

# `12-security-and-containment.md`

I'd explicitly assume that eventually Rootstock:

* executes untrusted code
* reads hostile web content
* receives prompt-injection attempts
* receives malicious customer emails
* installs dependencies
* operates infrastructure exposed to the public internet

So the security model is fundamental.

Explore:

* per-venture isolation
* credential segmentation
* sandbox execution
* secret storage
* network egress limits
* dependency scanning
* prompt-injection boundaries
* human-controlled policy engine
* lateral movement prevention

The important mental model:

> A compromised venture must not imply a compromised Rootstock.

---

# `13-observability-and-audit.md`

If Rootstock operates autonomously, you need to be able to answer:

> Why the hell did it do that?

Not from chain-of-thought.

From recorded organizational decisions.

Persist things like:

```text
decision
inputs
evidence
policy invoked
capital at risk
expected outcome
actual outcome
actor
timestamp
```

Example:

```text
Decision:
Increase TinyPDFThing Google Ads budget from $10/day to $18/day.

Evidence:
7-day CAC $4.20
30-day gross margin/customer $17.80

Authority:
venture-marketing-spend-v2

Capital impact:
+$56/week maximum

Review:
7 days
```

That's infinitely more useful than storing model reasoning.

---

# `14-failure-modes.md`

I'd have fun with this one.

Brainstorm every way this thing dies stupidly.

Examples:

* spends itself into bankruptcy
* API cost explosion
* endless build/no sales
* buys domains forever
* SEO spam factory
* support promises capabilities engineering hasn't built
* repeated reinvestment in sunk-cost projects
* catastrophic pricing mistake
* accidental refunds
* infrastructure compromise
* vendor bans
* account suspension
* fraudulent customer
* runaway recursive delegation
* duplicated ventures
* model provider outage
* poisoned institutional memory
* hallucinated revenue
* misclassified operating cost
* regulatory exposure
* customer PII leakage
* prompt injection through email
* optimization toward gross revenue instead of profit

For each, ask:

> What invariant should make this impossible or bounded?

---

# `15-human-intervention-model.md`

Define when you appear.

Ideally you are:

**shareholder + board + root administrator**

not:

**daily project manager.**

Categories:

```text
FYI
Rootstock informs you.

REVIEW
Rootstock requests judgment but can continue operating.

APPROVAL
Rootstock cannot proceed without authorization.

EMERGENCY
Rootstock automatically suspends activity and escalates.
```

Also define what Rootstock should do if you simply don't answer.

That matters a lot.

---

# `16-bootstrapping-rootstock.md`

The genesis story.

At T=0 Rootstock owns nothing.

What do you provide?

Maybe:

```text
$250 treasury
one AWS account
one Workspace account
one GitHub org
one rootstock domain
model API access
web research
payment processing
deployment capability
```

Then define milestones:

```text
M0 Rootstock boots
M1 creates first opportunity thesis
M2 receives approval for initial experiment
M3 deploys first property
M4 receives first external visitor
M5 receives first customer interaction
M6 receives first dollar
M7 reaches venture break-even
M8 reaches Rootstock operating break-even
M9 funds second venture entirely from earnings
```

That sequence would make a fantastic actual roadmap later.

---

# `17-success-metrics.md`

Avoid optimizing solely for revenue.

I'd track Rootstock-level metrics:

### Survival

```text
runway
monthly burn
reserve ratio
```

### Economic performance

```text
MRR
net income
ROIC
gross margin
capital efficiency
```

### Portfolio

```text
active ventures
profitable ventures
dead ventures
median time to validation
median time to first revenue
```

### Autonomy

```text
human interventions/month
human minutes/month
approval requests
successful autonomous decisions
```

### Learning

```text
hypotheses tested
institutional lessons reused
repeat failure rate
```

There's a gorgeous north-star metric hiding here:

> **Profit generated per human minute of intervention.**

Eventually Rootstock should drive that denominator toward zero.

---

# `18-open-questions.md`

This becomes the dumping ground for unresolved philosophical/architectural questions instead of prematurely deciding them.

Examples:

* Is Rootstock one model or model-agnostic?
* Does Rootstock have a persistent conversational identity?
* Does it control its own model selection?
* Can it spend money on better models?
* Can it build internal tools purely for itself?
* When does internal tooling count as capital expenditure?
* Can one venture loan capital to another?
* When does Rootstock abandon a market?
* Can it sell a venture?
* What happens to proceeds?
* Can it acquire an existing small website?
* Can it purchase datasets?
* Can it create another autonomous Rootstock-like organization?
* Should there be a hard prohibition on recursive autonomy?

That last one deserves a big red circle.

---

# Scenarios are especially valuable

I would absolutely include the `scenarios/` directory because abstract rules become much clearer when you walk them through.

For example, `runaway-cost.md`:

```text
At 02:13 UTC, Venture A's model bill jumps from $0.80/hour to $19/hour.

What detects it?

What stops it?

Does Rootstock:
- scale down?
- disable a feature?
- switch models?
- suspend the venture?
- notify the operator?

How much may it spend trying to recover?

What institutional lesson gets recorded?
```

Or `first-reinvestment.md`:

```text
Rootstock has earned $427 net.

Reserve requirement: $220.
Available capital: $207.

Three opportunities exist:

A: improve existing profitable venture
B: launch validated adjacent product
C: test entirely new market

How does Rootstock allocate the $207?
```

These scenarios will expose missing rules incredibly quickly.

---

## One architectural principle I'd put near the top of the entire repo

Something like:

> **LLMs propose. Deterministic systems constrain, execute, measure and account.**

Rootstock can decide that spending $37 makes sense.

It should **not** decide whether its own bank balance is $472 or $4,720.

Rootstock can propose that a deployment is healthy.

A health check determines whether it actually is.

Rootstock can conclude that a venture is profitable.

The accounting system determines whether that's true.

That boundary feels absolutely fundamental.

And another:

> **Autonomy is granted through capabilities, not assumed through intelligence.**

Rootstock isn't powerful because the model is smart.

Rootstock is powerful because a deterministic authority system gives it exactly the tools and money it is permitted to use.

That connects extremely naturally with the architecture you've already been exploring around deterministic orchestration and capability gates.
