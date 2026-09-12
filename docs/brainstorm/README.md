# Rootstock — Design Notebook

> Rootstock is an autonomous venture operating system. It receives bounded capital and
> capabilities, identifies commercial opportunities, creates and operates digital
> properties, learns from their outcomes, and reinvests retained earnings into further
> productive activity.

Rootstock is not an AI that makes money. Rootstock is an autonomous venture studio whose
employees happen to be agents, operating underneath a human legal entity that holds
actual ownership.

## What this directory is

This is the **conceptual notebook** — exploratory thinking, not decisions and not
implementation. Its purpose is to capture the things we do not want to rediscover six
months from now: what Rootstock is, what it is allowed to optimize for, what must remain
deterministic, what authority it can earn, how money flows, how ventures live and die,
and where human control remains absolute.

**Decisions have graduated out of here.** As of the design phase:

| Directory | Holds |
| --- | --- |
| `docs/brainstorm/` | Exploratory thinking. Contradictions allowed. This directory |
| `docs/design/` | Committed architecture. Contradictions are bugs |
| `docs/plans/` | How we intend to build it. Expected to evolve |
| `operations/` | What actually exists, as built |

Where this notebook and `docs/design/` disagree, **`docs/design/` wins.** This directory is
kept because the reasoning behind a decision is often more useful than the decision, but it
is no longer the authority on anything.

## Version numbering

The canonical version ladder lives in `16-bootstrapping-rootstock.md`:
**0.0 organism → 0.1 research → 0.2 sandbox building → 0.3 deployment → 0.4 external
contact → 0.5 bounded spending → 0.6 first venture → 1.0 first dollar.**

Two retired numbering schemes may appear in older commits: the `M0`–`M9` milestones, and an
earlier use of "0.1" to mean the entire journey to first revenue (now `1.0`). `16` carries
the mapping table. The `Status: Draft` header on each file refers to *document* maturity and
has nothing to do with the version ladder.

Ground rules for this directory:

- **These documents are exploratory.** They describe intent, not current behavior.
- **Contradictions are allowed for now.** Where two documents disagree, that disagreement
  is itself a finding. Log it in `18-open-questions.md` rather than papering over it.
- **Implementation decisions belong elsewhere, later.** No file here should specify a
  database schema, a framework, or a deployment topology.
- **Invariants should eventually graduate into formal specifications and tests.** The
  contents of `01-system-invariants.md` are the primary candidates. An invariant that
  cannot eventually be expressed as an assertion is probably a value statement, and
  should be relabeled as one.

## The two principles that sit above everything else

**1. LLMs propose. Deterministic systems constrain, execute, measure and account.**

Rootstock can decide that spending $37 makes sense. It must not decide whether its own
bank balance is $472 or $4,720. Rootstock can propose that a deployment is healthy; a
health check determines whether it is. Rootstock can conclude that a venture is
profitable; the accounting system determines whether that is true.

**2. Autonomy is granted through capabilities, not assumed through intelligence.**

Rootstock is not powerful because the model is smart. Rootstock is powerful because a
deterministic authority system gives it exactly the tools and money it is permitted to
use. Capability is the unit of trust, and it is always explicitly conferred.

## Reading order

If you are new, read `00`, `01`, and `02` in that order. They establish what we are
building, what must always be true, and what "autonomous" actually means here. Everything
else can be read on demand.

| Document | Answers |
| --- | --- |
| `00-vision.md` | What are we building, and why is it different? |
| `01-system-invariants.md` | What must be true regardless of architecture? |
| `02-autonomy-model.md` | What does "autonomous" mean, concretely and in degrees? |
| `03-economic-model.md` | How does money work inside Rootstock? |
| `04-governance-and-authority.md` | Who decides what? |
| `05-root-of-trust.md` | What stays exclusively human, and how do we stop it? |
| `06-memory-and-institutional-learning.md` | What does Rootstock know, and how does it stay true? |
| `07-venture-lifecycle.md` | How does a venture come into being and die? |
| `08-capital-allocation.md` | How does Rootstock choose where money goes? |
| `09-identity-and-external-presence.md` | Who does Rootstock claim to be in public? |
| `10-agent-organization.md` | What roles exist inside the organization? |
| `11-tools-and-capabilities.md` | What can Rootstock actually do, mechanically? |
| `12-security-and-containment.md` | How do we survive a compromise? |
| `13-observability-and-audit.md` | How do we answer "why did it do that?" |
| `14-failure-modes.md` | How does this die stupidly, and what bounds each case? |
| `15-human-intervention-model.md` | When does the operator appear, and what if they don't? |
| `16-bootstrapping-rootstock.md` | What exists at T=0, and what happens next? |
| `17-success-metrics.md` | How do we know it is working? |
| `18-open-questions.md` | What have we deliberately not decided? |
| `scenarios/` | Walkthroughs that stress-test the rules above. |

The `scenarios/` directory is disproportionately valuable. Abstract rules become clear
very quickly when walked through a concrete incident, and each scenario tends to expose a
missing rule within a page.

## Status conventions

Because this is a first pass, most content is proposed rather than settled. Every
significant claim carries one of three markers:

- **`[SETTLED]`** — follows directly from the founding brainstorm and is unlikely to
  change without a deliberate reversal.
- **`[PROVISIONAL]`** — a concrete default chosen so the design has something to push
  against. Reasonable, but explicitly awaiting confirmation. Change these freely.
- **`[OPEN]`** — genuinely undecided. Every `[OPEN]` marker should have a corresponding
  entry in `18-open-questions.md`.

Invariants are given stable IDs (`FIN-1`, `CTL-3`, and so on) so that other documents and
eventually test names can reference them without ambiguity. Invariant IDs are append-only:
if one is retired, mark it retired rather than reusing the number.

## Relationship to Argus

Argus (a sibling repository) is the closest architectural cousin to Rootstock: a
local-first, artifact-audited operator system that runs deterministic gates over a
portfolio of software products. It is a working system, not a design exercise, and it has
already solved several problems Rootstock will otherwise solve twice.

The overlap is deliberate and worth preserving:

- Argus enforces permissions through declarative per-product YAML evaluated by
  deterministic Python **before** execution, with LLM paths explicitly non-authoritative.
  That is the same posture as Principle 1 above.
- Argus already has autonomy modes and rollout tiers, execution approvals, capability gap
  records, sandboxed execution, and versioned inspectable artifacts under `runs/`.
- Argus vocabulary worth reusing verbatim where it fits: the permission values
  `yes` / `no` / `confirm`; the grant responses `confirm_once` / `always` / `no`; the
  lifecycle stages `idea` / `build` / `validate` / `grow` / `maintain` / `decline` / `kill`;
  and the practice of versioning every persisted artifact with a schema id.

What is genuinely new in Rootstock is the economic layer. Argus governs *what may be done
to a product*. Rootstock governs *whether a product should exist at all, and what it is
worth spending on it*. Capital allocation, treasury, unit economics, and venture birth and
death have no Argus equivalent.

**Decision `[SETTLED]`: separate implementations, shared vocabulary.** Rootstock is built
alongside Argus rather than on top of it. The two systems deliberately converge on
terminology and enforcement *patterns* — deterministic gates ahead of execution, declarative
scoped permissions, versioned inspectable artifacts, capability requests — without coupling
their code.

The reasoning: Argus governs actions on products that already exist, while Rootstock's
distinctive layer is economic and decides whether a product should exist at all. Coupling
them would constrain both, and the borrowed value here is conceptual rather than mechanical.
Where this notebook cites Argus, it is citing a proven pattern worth copying, not a
dependency.
