# 06 — Memory and Institutional Learning

> Status: Draft.

Rootstock's compounding knowledge may eventually matter more than its compounding capital.
Capital grows linearly with good decisions. Knowledge changes the *quality* of every future
decision, which is a multiplier.

This is also where Rootstock most obviously differs from an agent framework. A framework
has a context window. An organization has institutional knowledge that outlives any
particular participant, task, or venture.

## The central design commitment

**Institutional memory should behave like a knowledge base, not like autobiographical
embeddings.** `[SETTLED]`

The failure mode being avoided: Rootstock accumulates a large vector store of everything it
has ever seen, retrieves plausible-sounding fragments, and slowly develops confident false
beliefs with no way to audit or correct them. That is not memory. That is drift with good
recall.

The alternative is structured claims with provenance, confidence, and expiry — closer to a
research database than a diary.

## Memory classes

Different memory has genuinely different requirements. Storing it all the same way is the
root mistake.

| Class | Contents | Authority | Mutability |
| --- | --- | --- | --- |
| **Constitutional** | Charter, invariants, capability grants, limits | Human-written | Read-only to Rootstock (CTL-3) |
| **Identity** | Who Rootstock is, ownership structure, values, voice | Human-written | Read-only |
| **Financial** | Ledger, transactions, balances, P&L | Deterministic system | Append-only (MEM-2) |
| **Venture state** | Architecture, config, roadmap, pricing, status, customers | Rootstock + systems | Current-state, versioned |
| **Relationship** | Customers, conversations, history, obligations | Rootstock + inbound | Append-only history, mutable summary |
| **Episodic** | What happened and when: decisions, actions, outcomes | Deterministic capture | Append-only (MEM-2) |
| **Institutional** | Reusable lessons, market observations, hypotheses, failures | Rootstock-derived | Claims with decay |
| **Source documents** | Research, competitor pages, docs, vendor terms | External | Immutable snapshots with fetch date |

Two boundaries carry most of the safety weight:

- **Financial memory is never model memory** (FIN-4). Rootstock reads balances; it never
  recalls them. Any figure a model states about money is a claim requiring verification.
- **External content never writes directly to institutional memory** (MEM-3). A customer
  email cannot become a lesson without internal derivation. This is the primary defense
  against poisoned memory, which is otherwise a very cheap attack.

## The claim record

Institutional memory's atomic unit. Everything Rootstock "knows" about the world, as
opposed to what it can look up, takes this form:

```text
claim          "Google Ads CAC for PDF utility keywords is roughly $47"
evidence       [link to campaign data, decision id, source snapshot]
derived_from   venture-003, campaign-2, 412 clicks, 9 conversions
timestamp      2026-03-14
confidence     medium
applicability  paid search; developer-tool utilities; US market
last_validated 2026-03-14
expires        2026-09-14
status         active | stale | superseded | refuted
supersedes     claim-0091
```

Why each field earns its place:

- **Evidence and derived_from** make a claim auditable. A lesson nobody can trace is a
  rumor, and rumors compound badly.
- **Confidence** prevents a single observation from carrying the weight of a validated
  pattern. Nine conversions is not a law of nature.
- **Applicability** is the field most often omitted and most often needed. "CAC is $47" is
  useless without knowing for what, where, and when. Overgeneralized claims are how a
  system learns the wrong lesson from a real experience.
- **Expiry** forces revalidation. Market facts decay; some decay fast.
- **Status and supersedes** mean knowledge is corrected by *replacing* rather than editing
  (MEM-2), preserving the history of what Rootstock believed and when.

## What should decay

If Rootstock once learned "Google Ads CAC for this niche is $47," that must not become
eternal truth. Suggested default lifetimes `[PROVISIONAL]`:

| Kind of claim | Default expiry |
| --- | --- |
| Pricing observed in a market | 3 months |
| CAC / conversion rates | 3 months |
| Competitor state | 6 months |
| Vendor pricing and terms | 6 months |
| Technical approach worked / did not work | 12 months |
| Regulatory or platform policy | 6 months |
| Structural lesson about Rootstock's own operation | No expiry, but revalidate annually |

An expired claim is not deleted. It moves to `stale` and can still be cited, but a decision
resting primarily on stale claims should be flagged in its decision record (`13`). "We
decided this based on year-old data" is exactly the kind of thing that should be visible in
hindsight.

## Lessons worth keeping

The founding brainstorm's examples are the right shape:

> Newsletter businesses relying on SEO took too long to validate.

> Users converted 3× better when the tool produced an immediate artifact.

> Firebase created too much baseline cost for tiny experiments.

Each is specific, actionable, and derived from a real outcome. Compare with useless
versions: "marketing is important," "users like good products," "watch your costs." The
test for whether a lesson is worth storing: **would it change a future decision?** If it
cannot flip a choice, it is an observation, not a lesson.

**Negative results are the most valuable and least likely to be recorded.** A venture that
failed for a legible reason is worth more than one that succeeded for unclear reasons.
Killing a venture should *require* producing a lesson (`07`) — it is the moment the
information is freshest and the incentive to move on is strongest.

## Preventing poisoned memory

Institutional memory is a high-value attack target: corrupt it once and you influence every
subsequent decision, with no obvious moment of compromise.

Defenses:

- **MEM-3**: external content cannot write directly. Promotion requires internal derivation
  with cited evidence.
- **Provenance is mandatory.** A claim whose only evidence is untrusted input is rejected at
  the schema level, not by judgment.
- **Source documents are stored as immutable snapshots**, separate from claims. What a web
  page said on a date is a fact; what it implies is a claim.
- **Claims that influence spending decisions get more scrutiny.** `[PROVISIONAL]` — claims
  cited in decisions above a capital threshold require either direct first-party evidence
  or two independent sources.
- **Periodic contradiction sweep.** Look for claims that conflict, and resolve rather than
  letting both persist. Two contradictory active claims mean retrieval order determines
  behavior, which is a silent nondeterminism.

## Relationship memory

The scenario worth designing for: a customer writes "Hey Rootstock, the CSV export still
breaks accented characters." Six months later, Rootstock should know exactly who that is
and what happened.

This requires: a durable customer record spanning conversations, linkage between support
history and product changes, and awareness of commitments made. **Promises are obligations**
and belong in relationship memory, not in a transcript — a commitment made and forgotten is
one of the fastest ways to lose a small customer base.

Constraints: customer data is PII, is subject to the security model in `12`, is
venture-scoped rather than portfolio-wide by default `[PROVISIONAL]`, and must be
deletable on request. That last one interacts awkwardly with append-only history (MEM-2)
and needs resolution — probably deletion of personal identifiers while preserving the
anonymized episodic record.

## Forgetting

Some things should be deleted outright, not merely expired:

- Customer PII beyond a retention period or on request
- Secrets that were accidentally captured
- Raw content of external communications, once summarized `[PROVISIONAL]`
- Verbose intermediate artifacts with no decision value

Never deleted: the ledger, decision records, audit trail, venture history, and lessons.
These are the organizational record and are append-only (MEM-2).

## What Rootstock should be able to answer

A practical test set for the memory design. If these are hard to answer, the design is
wrong:

- "Have we tried something like this before, and what happened?"
- "What do we believe about this market, and how confident are we, and how old is that?"
- "Who is this customer and what have we promised them?"
- "Why did we choose this architecture for Venture B?"
- "What did we spend on Venture C, in total, ever?"
- "What lessons have we recorded that apply to this proposal?"
- "What did we believe six months ago that we now think was wrong?"

The last one is the real test of whether this is a knowledge base or a pile of embeddings.

## Open questions

- Should institutional memory be shared across ventures by default, or namespaced with
  explicit promotion? Leaning: venture-scoped by default, promoted deliberately, because
  premature generalization is the main way a lesson becomes wrong.
- How does Rootstock avoid the "everything is a lesson" failure, where the knowledge base
  fills with low-value claims and retrieval degrades? Possibly a cap on active claims,
  forcing consolidation.
- Should Rootstock be able to *refute* its own prior lessons autonomously, or does that
  require review? Leaning autonomous with a record, since a system that cannot update is
  worse than one that occasionally updates wrongly.
- Does institutional memory survive a full rebuild of Rootstock's implementation? It must —
  which argues for a storage format independent of any framework or model. Worth treating
  as a hard requirement rather than a preference.
