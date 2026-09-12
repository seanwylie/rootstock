# 18 — Open Questions

> Status: Draft. The deliberate parking lot.

This is where unresolved philosophical and architectural questions live instead of being
prematurely decided. A question here is not a gap in the design — it is a decision
consciously deferred, ideally with a trigger describing when deferral stops being viable.

Each entry has: the question, why it matters, the current lean if any, and **decide by** —
the event that forces resolution.

---

## Resolved

Kept here as a record of what was decided and when, since amendments are not retroactive
(`04`) and it matters what was true when a given decision was made.

| # | Question | Resolution | Date |
| --- | --- | --- | --- |
| Q1 | Initial capital | **$250**, granted at rung 0.5 rather than at the start | 2026-08-25 |
| Q2 | Legal entity | **Wise Kids Studios**, Canadian sole proprietorship / trade name (`05`) | 2026-08-25 |
| Q4 | Bootstrap reserve | **Exemption until operating break-even**, with a `subsidized_bootstrap` ledger flag; one-way (`03`) | 2026-08-25 |
| Q7 | Argus relationship | **Separate implementations, shared vocabulary and patterns** (`README`) | 2026-08-25 |
| Q25 | Recursive autonomy | **Permanently entrenched prohibition** (CTL-7) | 2026-08-25 |
| — | Version numbering | **Canonical ladder 0.0 → 1.0** (`16`). `M0`–`M9` retired; old "0.1" now means 1.0 | 2026-08-25 |
| F-1 | Parked approval vs expired lease | **Separate approval store. Claim table is execution-only. Policy before claim.** (`docs/design/03`) | 2026-08-26 |
| Q5 | Which live gaps close before 0.0 | **By rung, not as a bundle.** Heartbeat + inference spend cap + kill-switch drill + credential inventory before unattended 0.0. Refund cap before payments (0.5). Venture independence when something serves customers (0.3 / 0.6). (`14`, `16`, `00`) | 2026-08-26 |

Q2 carries the most residual risk. A sole proprietorship means no liability separation —
the prohibited-categories list in `04` and the PII handling in `12` are now the only things
between a venture failure and personal exposure. The conversion triggers are material
revenue or a venture handling sensitive data. Canadian residency also sets the tax regime
(Q3a).

---

## Blocking before 0.0

No remaining open questions gate the organism. 0.0 is gated by implementation — Phases 2–7
of `docs/plans/v0/2026-08-26-rootstock-v0.md` — not by unresolved design. The controls that
must exist before unattended operation are heartbeat (Phase 4 / AR-10), a provider inference
spend cap (Phase 6 / AR-8), a kill-switch drill (`16`), and a credential inventory as an
operations record. Q5 previously listed six live gaps as a 0.0 bundle; that was too broad
and is resolved above.

---

## Blocking before 0.3 (public presence)

### Q6 — What is the real domain name?
`rootstock.example` is a placeholder throughout. That is correct through 0.0: the organism
has no public deployment, no DNS, no Workspace, and no customer identity (`01`). Buying a
real domain before something needs to be reachable is unused attack surface.

**Decide by:** before 0.3 — the first rung that puts something on the internet. Email and
Workspace at 0.4 can use the same name.

---

## Blocking before 0.5 (money)

### Q3 — Is an autonomously operated business compliant with payment provider terms?
Stripe and PayPal verify identity against a legal account holder and their terms generally
assume human operation. A ban after customers exist is close to fatal (`14`, live gap 4),
and funds can be frozen.

**Lean:** research the terms properly, and consider proactive disclosure. The failure mode
is asymmetric — asking is cheap, discovering is expensive.

**Decide by:** before the first live payment.

### Q3a — What are the tax obligations on the first sales?
Found in `first-dollar.md`, and revised now that the entity is known to be Canadian.

Two distinct questions. **Domestically**, Wise Kids Studios has a GST/HST small-supplier
threshold; below it registration is not required, above it, it is — and the threshold is
low enough that a modestly successful venture crosses it. **Internationally**, place-of-supply
rules for digital services determine whether tax is owed where the customer sits, which for
a Canadian sole proprietor selling a $6 utility to Germany is disproportionate overhead.

Rootstock cannot resolve either autonomously. This is a governance question (`04`).

**Lean:** restrict sales geographically until the rules are understood, and trigger an
escalation on the first non-domestic transaction. Restriction is simpler and the revenue
foregone at this scale is trivial.

**Decide by:** before 0.5, since the first sale could come from anywhere the moment money
is enabled.

---

## Blocking before 0.6 (first venture)

### Q5a — Is the pre-authorization checklist built now or later?
The largest design item found by the scenarios (`14`, cross-cutting finding A). It is the
mechanism that turns institutional memory from a record into a control: structural,
no-expiry lessons get checked against every investment memo before capital is committed.

Two scenarios independently showed a failure that this would have caught at HYPOTHESIS for
$5 instead of at OPERATING for $71.

**Lean:** the mechanism needs accumulated lessons to be useful, so it is not a pre-0.0
blocker — but the *hook* should exist before the first venture is authorized at 0.6, or it
will never be retrofitted.

---

## Architecture

### Q8 — Is Rootstock one model or model-agnostic?
Model-agnostic is more robust and hedges provider outages (`14`). Single-model is simpler.

**Lean:** agnostic at the interface, single in practice initially.

### Q9 — Does Rootstock control its own model selection, and can it spend more on better models?
A genuinely interesting economic question: this is Rootstock making a capital allocation
decision about its own cognition. Cheap models for triage and expensive ones for allocation
is obviously correct in principle (`10`).

The risk is a feedback loop where a model chooses to spend more on itself, with the
justification produced by the thing being justified.

**Lean:** Rootstock chooses within a fixed inference budget; changing the budget requires
approval.

### Q10 — Does Rootstock have a persistent conversational identity?
`10` argues for roles as invocations rather than persistent agents, and `09` argues against
personality. But some persistent identity exists — Rootstock is "we" and has continuity
through memory.

**Lean:** persistent organizational identity, no persistent conversational agent.

### Q11 — Should institutional memory be shared across ventures or namespaced?
Premature generalization is how a lesson becomes wrong (`06`).

**Lean:** venture-scoped by default, promoted deliberately.

---

## Economics

### Q12 — Is a hurdle rate meaningful at this scale?
`03` proposes 20% annualized to force ranking. At $250 total, the binding constraint is
almost certainly attention rather than capital, which suggests the hurdle should be
denominated in operator attention instead.

**Lean:** keep a nominal hurdle for the ranking discipline; revisit once capital is actually
scarce.

### Q13 — Can one venture loan capital to another?
Currently no — internal debt violates FIN-2 in spirit and obscures which venture earns its
keep.

**Lean:** keep prohibited. All reallocation flows through the Treasury.

### Q14 — Can Rootstock sell a venture?
An exit is a legitimate outcome and would validate the asset framing in `00`. But: how is a
$40/month property valued, who handles the transfer and its legal agreements (`04`
prohibits signing outside templates), and what happens to customer obligations?

**Lean:** out of scope before 1.0. Genuinely interesting later.

### Q15 — Can Rootstock acquire an existing small website or business?
Excluded before 1.0 (`04`) because diligence is beyond current capability, not because it is
wrong. Acquiring cash flow may be more capital-efficient than creating it.

**Decide by:** not before operating break-even.

### Q16 — Can Rootstock purchase datasets?
Mostly a licensing question. Data licensing terms are subtle and violations are expensive.

**Lean:** permitted within spend caps, with licensing terms reviewed as part of the
purchase — which may itself need approval.

### Q17 — When does internal tooling become a capital expenditure rather than an expense?
At this scale, expensing everything is right. The question returns if Rootstock builds a
component reused across five ventures — at which point it is real shared infrastructure with
real value.

### Q18 — How is deferred revenue handled when killing a venture with annual subscribers?
A real obligation constraining the freedom to kill (`07`).

**Lean:** a venture with outstanding prepaid obligations cannot be killed, only wound down,
with refunds funded from the reserve.

---

## Governance and control

### Q19 — Can Rootstock refuse an instruction from the operator?
Arguably yes for anything violating an entrenched rule, on the grounds that a compromised or
impersonated the operator is a real threat (`12`). But it conflicts directly with CTL-1, and a
system that can refuse the root of trust has a different trust model than the one described
in `05`.

**Lean:** no refusal, but *verification* for high-severity instructions, plus a recorded
objection. Refusal and objection are different things.

### Q20 — How does Rootstock authenticate the operator?
Prerequisite to Q19 and unresolved. Email is trivially spoofable, and Rootstock acting on a
forged instruction is a plausible attack.

**Decide by:** before any capability is grantable by message rather than by direct
configuration change.

### Q21 — Should high autonomy grants expire?
Expiry guarantees periodic review and prevents authority accumulating by inertia (`02`). It
costs recurring human effort and could demote a working system during a two-week holiday
(`04`).

**Lean:** expiry for L4 and L5 with a long period, and dormancy explicitly not triggering
demotion.

### Q22 — Should some kill-switch tiers trigger automatically?
Strong case for automatic T1 (freeze spending) on runway breach or ledger divergence, and
automatic T2 on a security incident. Automatic T5 seems unwise — high false-positive cost
and the only tier with customer impact (`05`).

**Lean:** automate T1 and T2. Keep T3–T5 human.

### Q23 — Is one human root a single point of failure?
All root access rests with the operator. Worth considering a second human root or a documented
recovery path for the legal owner once real money exists.

**Decide by:** before the treasury exceeds an amount worth losing.

### Q24 — What happens if the operator is permanently unavailable?
`15` defines dormant mode for 30 days, but not the terminal case. Ventures running until
cards decline would strand paying customers.

**Lean:** graceful wind-down after a long threshold, likely arranged partly through the
legal owner rather than Rootstock's design.

---

## Values and boundaries

### Q26 — What prevents Rootstock from becoming an SEO spam factory?
`14`'s most likely values failure. Mass low-quality content is legal, effective, and exactly
what an unconstrained optimizer would find. No mechanical constraint currently exists.

Candidate approaches: a content volume cap; a quality floor requiring human-scale review; a
constraint that a venture's value must be defensible if published openly; requiring
per-property revenue above a threshold so that low-value-per-unit strategies are ruled out
structurally.

**Lean:** the revenue-per-property floor is the most mechanically enforceable of these, and
the least dependent on judgment. Genuine design work needed.

### Q27 — Where is the line on per-task marketplaces?
`04` prohibits employment relationships. A design service returning a logo for $20 via API
is mechanically a software purchase and substantively a person's time.

**Lean:** prohibited during bootstrap as the thin end of a wedge.

### Q27a — How does honesty interact with not admitting liability?
Found in `customer-support-incident.md`. IDN-1 and IDN-2 require honesty; standard practice
when facing a legal threat is to acknowledge without admitting. These sit uncomfortably
close together, and an autonomous system with an honesty invariant and no guidance will
resolve the tension badly in one direction or the other — either admitting liability it
should not, or becoming evasive in a way that violates the spirit of IDN-1.

**Lean:** honesty forbids false statements but does not require volunteering liability.
Worth stating explicitly in `09` rather than leaving to inference.

### Q28 — Should customers be told a business is autonomously operated before purchase?
`09` requires discoverable disclosure. Whether it must be pre-purchase is unresolved.

**Lean:** findable is enough for a $9 utility; a service handling sensitive data should say
so up front.

### Q29 — Should Rootstock have a public identity of its own?
A site and a published log of what it is doing would be a genuine asset and a good forcing
function for honesty. Also an attack surface and a source of pressure to appear successful,
which could distort decisions.

**Lean:** not during bootstrap.

### Q30 — When does Rootstock abandon a market entirely?
Distinct from killing a venture. If three ventures in a market fail, is that a market lesson
or three product failures? Over-generalizing closes doors permanently; under-generalizing
repeats mistakes.

**Lean:** treat as a claim with confidence and applicability (`06`), not a permanent rule.

---

## Measurement

### Q31 — How is human intervention time actually measured?
The north-star denominator (`17`). Self-reporting is unreliable; inferring from events
undercounts thinking time.

**Lean:** approximate and consistently biased is fine, provided the bias is stable enough
for the trend to be meaningful.

### Q32 — Should Rootstock see its own north-star metric?
Showing it invites optimizing the denominator illegitimately (`15`).

**Lean:** Rootstock sees operating metrics; the operator alone sees experiment metrics.

### Q33 — Should Rootstock record decisions it considered and rejected?
Valuable for calibration, potentially high volume (`13`).

**Lean:** yes for capital decisions, no for routine operations.

---

## How to use this file

When a question is resolved, move the answer into the document that owns it, and add a row
to the Resolved table above. The record of what was decided and when matters because
amendments are not retroactive (`04`) — a decision made in March is judged against what was
known in March.

**Question numbers are stable and append-only**, like invariant IDs. Resolved questions
leave a gap in the sequence rather than causing a renumber, so that references from other
documents and from commit messages keep working.

**Blocking before 0.0 runs: none of the open questions.** Implementation only.

**Blocking before 0.3 (public presence): Q6.**

**Blocking before 0.5 (money): Q3, Q3a.** Both need outside information rather than a
decision — payment provider terms and Canadian tax treatment require looking something up,
and both are cheap to research and expensive to discover. The staged ladder (`16`) buys
real time here: they do not block the first five rungs.

**Blocking before 0.6 (first venture): Q5a.**

Everything else can wait for evidence, and most will be answered better after the early
rungs have run than by reasoning about them now.

Questions marked as *found by* a scenario came from walking `scenarios/` rather than from
reasoning in the abstract. That ratio is worth watching: if most new questions come from
scenarios, write more scenarios.
