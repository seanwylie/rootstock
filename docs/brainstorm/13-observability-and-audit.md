# 13 — Observability and Audit

> Status: Draft.

If Rootstock operates autonomously, the question that must always be answerable is:

> Why the hell did it do that?

**Not from chain-of-thought. From recorded organizational decisions.** `[SETTLED]`

This distinction is the whole document. Model reasoning is verbose, post-hoc,
unverifiable, and frequently a plausible story rather than the actual cause. A decision
record is short, structured, verifiable against outcomes, and comparable across time.

Storing reasoning creates the *illusion* of observability while making real analysis
harder, because the volume is high and the signal is low. Storing decisions creates an
organizational record.

## The decision record

The core artifact:

```text
id               dec-0417
timestamp        2026-03-14T09:22:00Z
actor            Governor
venture          venture-002
decision         Increase TinyPDFThing Google Ads budget from $10/day to $18/day
alternatives     hold at $10/day; pause campaign; shift budget to venture-003
inputs           7-day CAC $4.20
                 30-day gross margin per customer $17.80
                 current MRR $84
evidence         [claim-0231 conf:high]  [ledger query lq-8891]
policy_invoked   venture-marketing-spend-v2
authority        L2 acquisition, within venture-002 remaining budget
capital_at_risk  +$56/week maximum
expected_outcome CAC remains below $8; +6 customers/week
review           2026-03-21
─────────────────────────────────────────────────
actual_outcome   [filled at review]
variance         [filled at review]
```

Why each field earns its place:

- **alternatives** — a decision without alternatives is a rationalization. This field is
  what makes `08` allocation honest.
- **evidence** with claim ids and confidence — links to `06`, and reveals when a decision
  rested on stale or low-confidence claims.
- **policy_invoked** and **authority** — proves the action was within granted authority
  (OPS-3), and makes unauthorized action detectable rather than merely forbidden.
- **capital_at_risk** — bounded downside, stated in advance (FIN-8).
- **expected_outcome** — the single most valuable field, and the one most likely to be
  omitted. Without a pre-registered expectation, every outcome can be narrated as expected.
- **actual_outcome / variance** — closes the loop. This is the raw material for
  calibration.

## Calibration is the point

An expected outcome recorded before the fact, compared to what happened, across hundreds of
decisions, answers a question nothing else can:

> **Is Rootstock's judgment any good, and is it improving?**

This is measurable rather than impressionistic. Systematic optimism, chronic
underestimation of time to revenue, overconfidence in a particular venture type — all
become visible in aggregate, and all are invisible in any individual decision.

Calibration data should feed institutional memory (`06`) as claims about Rootstock's own
behavior: *"We have historically underestimated time-to-first-revenue by roughly 3×."* A
lesson of that kind is worth more than most market observations, because it applies to
every future decision.

## What must be recorded

Per OPS-3, anything that spends money, changes external state, communicates outward, or
alters venture status:

| Event | Record |
| --- | --- |
| Capital allocation | Full decision record + investment memo (`08`) |
| Any expenditure | Transaction with attribution (FIN-3) and causing decision |
| Lifecycle transition | State change, evidence, criteria met (`07`) |
| Deployment | What, where, by whom, rollback point |
| Outbound communication | Message, recipient, identity used, causing decision (IDN-3) |
| Pricing change | Old, new, rationale, expected effect |
| Capability use | Which, scope, by which role, outcome |
| Capability grant or revocation | Who authorized, scope, why |
| Approval request and response | Full context, decision, latency |
| Refund | Amount, reason, customer, authority |
| Incident | Detection, containment, blast radius, resolution |
| Kill | Post-mortem, final P&L, lessons (`07`) |
| Claim promoted to institutional memory | Claim, evidence, derivation |
| Invariant violation | What, how detected, what was in flight |

**If the audit write fails, the action does not proceed** (OPS-3). Audit is part of the
execution path, not a side effect. This is a real constraint on implementation and worth
accepting: an action that happened without a record is indistinguishable from an action
nobody authorized.

## Properties of the record

- **Append-only** (MEM-2). Corrections append; history never changes.
- **Rootstock cannot delete from it** even with its own credentials (`05`). An audit log the
  operator can erase is not evidence.
- **Versioned schemas.** Argus versions every persisted artifact with a schema id
  (`argus.audit_bundle.v1` and similar). Worth copying exactly — a five-year record is
  worthless if the format silently changed in year two.
- **Queryable by venture, time, actor, capability, and capital.**
- **Linked.** Decisions reference evidence, transactions reference decisions, outcomes
  reference expectations. The graph is what makes reconstruction possible.

## Operational telemetry

Distinct from decision records — high volume, shorter retention, machine-generated:

- Health checks and uptime per venture
- Error rates and latency
- Traffic and conversion funnels
- Spend rate by category, continuously
- Inference token consumption by role and venture
- Capability invocation counts
- Queue depth and loop timing

Telemetry answers "what is happening." Decision records answer "why." Both are needed, and
conflating them produces a system where neither question is answerable.

**Spend rate telemetry deserves special mention**: it is the input to the runaway-cost
detection in `14` and `scenarios/runaway-cost.md`, and it needs to be near-real-time.
Discovering a cost explosion from a monthly bill is discovering it far too late.

## The verification layer

Recording what Rootstock *believes* it did is insufficient. Independent verification, per
the Auditor role (`10`):

- **Ledger vs. providers.** Internal ledger reconciled against bank, Stripe, and cloud
  billing (FIN-4). Divergence is EMERGENCY.
- **Inventory vs. reality.** Every live resource maps to a registered owner (OPS-1). Catches
  orphans, which are both cost and attack surface.
- **Decisions vs. actions.** Every state-changing action traces to a decision record, and
  every decision record's stated action actually happened. Both directions matter: an action
  without a decision is unauthorized; a decision without an action is a system that thinks
  it did something it didn't.
- **Claims vs. evidence.** Institutional memory claims still have valid provenance (MEM-1).
- **Constitution integrity.** Hash verification (CTL-3).
- **Capability grants vs. holdings.** Every held credential traces to a human grant (CTL-4).

The third check is the one that catches the most insidious failure: **Rootstock believing
something false about itself.** A system whose self-model has drifted from reality will make
confident, well-reasoned, catastrophically wrong decisions, and nothing else in this
notebook detects that.

## Reporting to the operator

The interface the operator actually uses (`15`). Design goal: **understand the state of the business
in under five minutes** `[PROVISIONAL]`.

**Weekly digest:** treasury and runway; each venture's status and P&L; decisions made, with
capital at risk; approvals pending; variances from expectation; incidents; new lessons; the
autonomy metrics from `17`.

**On-demand:** full decision history, venture detail, ledger, audit query.

**Immediate:** anything EMERGENCY-class.

The digest should lead with what changed and what needs attention, not with a wall of
metrics. A report the operator skims is worse than a shorter one they read.

## Retention

`[PROVISIONAL]`

| Data | Retention |
| --- | --- |
| Decision records | Forever |
| Ledger | Forever |
| Lifecycle history | Forever |
| Institutional memory | Forever, with decay status (`06`) |
| Audit log | Forever |
| Operational telemetry | 90 days, aggregated thereafter |
| Raw model interactions | 30 days `[OPEN]` |
| Customer PII | Per venture policy, deletable |
| Secrets | Never logged |

`[OPEN]` — how long to keep raw model interactions. They are useful for debugging and
occasionally for understanding a decision that the record captured poorly. They are also
bulky, contain PII, and represent the chain-of-thought this document argues against relying
on. Thirty days is a compromise.

## Open questions

- What is the minimum viable decision record? The full schema is heavy for a $3 decision.
  Probably tiered by capital at risk, with the risk that the cheap tier becomes the default.
- Should Rootstock record decisions it *considered and rejected*? Enormously valuable for
  calibration, and potentially high volume.
- How is variance measured for qualitative expectations? "CAC stays below $8" is checkable;
  "customers will find this valuable" is not. Possibly expected outcomes should be required
  to be checkable.
- Does the Auditor's independence need to extend to separate storage that Core cannot write?
  Leaning yes.
