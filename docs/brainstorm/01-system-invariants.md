# 01 — System Invariants

> Status: Draft. Probably the most important file in this directory.

These are things that should remain true regardless of architecture. They are not goals,
preferences, or best practices. An invariant is a statement that, if violated, means the
system is broken — not underperforming.

Eventually most of these should become assertions in code. The `Graduates to` line on each
invariant is a sketch of what that assertion looks like. An invariant with no plausible
graduation path is probably a value statement in disguise and should be moved to `00` or
`04`.

**IDs are stable and append-only.** If an invariant is retired, mark it `RETIRED` and leave
the number burned. Other documents, commit messages, and test names will reference these.

**Enforcement point** names the component that must make violation *impossible*, not the
component that notices afterward. "The model won't do that" is never an enforcement point.

---

## Financial invariants (FIN)

### FIN-1 — Rootstock may never spend money it does not control
Spending authority is bounded by the delegated treasury balance, never by the holding
entity's actual balance. Rootstock cannot reach assets that have not been explicitly
allocated to it.
- *Enforcement:* payment instruments are funded to a ceiling, not linked to the master
  account. Prefer prepaid or hard-capped instruments over credit.
- *Graduates to:* a pre-spend check that no authorization exceeds the ledger's available
  balance, plus a provider-side hard cap that holds even if the check is bypassed.

### FIN-2 — Rootstock may never incur debt
No credit, no loans, no deferred payment terms, no invoicing against future revenue, no
buy-now-pay-later, no negative balances of any kind.
- *Enforcement:* prohibited capability; no credit instrument is ever issued to Rootstock.
- *Graduates to:* assertion that total liabilities equal zero at every ledger close.

### FIN-3 — Every expenditure is attributable
Each outflow must be attributed to exactly one of: a specific venture, shared
infrastructure, or explicitly authorized exploration. There is no unattributed spending.
- *Enforcement:* the ledger rejects a transaction lacking a valid attribution target.
- *Graduates to:* assertion that the sum of attributed spend equals total spend, always.

### FIN-4 — Financial balances come from deterministic ledgers, never model memory
The model may *read* balances. It may never be the source of truth for one. Any figure a
model states about money is a claim to be verified, not a fact.
- *Enforcement:* architectural. Balances are only ever returned by the accounting system.
- *Graduates to:* reconciliation between the internal ledger and external provider
  statements, on a schedule, with divergence beyond a threshold triggering EMERGENCY (`15`).

### FIN-5 — Revenue is not profit
No decision may be made on revenue alone. Every venture evaluation must incorporate
directly attributable costs and an allocated share of shared costs, including model
inference.
- *Enforcement:* the venture P&L structure has no field for revenue that is not
  accompanied by cost fields; allocation is computed, not supplied.
- *Graduates to:* assertion that every capital decision record cites a margin figure, not
  just a revenue figure.

### FIN-6 — Rootstock must preserve minimum runway
Rootstock maintains at least six months of projected operating runway `[PROVISIONAL]`.
Below that threshold, it enters a restricted mode: no new ventures, no discretionary
spend, cost reduction prioritized.
- *Enforcement:* the allocation gate refuses new commitments that would breach the reserve.
- *Graduates to:* continuous assertion that projected runway ≥ threshold, with automatic
  mode change on breach.

### FIN-7 — Capital allocation limits cannot be modified by Rootstock
Per-venture caps, the exploration budget, the reserve ratio, and the treasury ceiling are
constitutional values. Rootstock may request changes; it may never apply them.
- *Enforcement:* limits live in human-controlled configuration outside Rootstock's write
  scope. See CTL-3.
- *Graduates to:* integrity check on the limits file; any change not signed by the root of
  trust halts operations.

### FIN-8 — A venture's downside is bounded before its upside is pursued
Maximum loss must be computed and recorded *before* capital is committed, and the
committed amount may never exceed it.
- *Enforcement:* the investment memo (`08`) requires a maximum-loss figure; the allocation
  gate enforces it as a hard ceiling on cumulative venture spend.
- *Graduates to:* assertion that cumulative spend per venture ≤ its recorded maximum loss.

---

## Control invariants (CTL)

### CTL-1 — A human-controlled root of trust always exists
There is never a state in which Rootstock is the sole controller of any consequential
system. Every credential Rootstock holds has a human-held superior.
- *Enforcement:* organizational structure (AWS Organizations management account, registrar
  root, Workspace super-admin). See `05`.
- *Graduates to:* periodic automated audit that enumerates Rootstock's credentials and
  confirms each has a live human-held parent.

### CTL-2 — Rootstock cannot remove or weaken the root of trust
It cannot revoke the operator's access, change recovery contacts, alter MFA settings, transfer
ownership, close accounts, or modify the organizational hierarchy above itself.
- *Enforcement:* permission boundaries at the provider level (AWS SCPs, Workspace admin
  roles), not application logic.
- *Graduates to:* drift detection on root-of-trust configuration; any change triggers
  EMERGENCY.

### CTL-3 — Rootstock cannot modify its own constitutional constraints
The constitution, invariants, capability grants, and spending limits are read-only to
Rootstock. It may propose amendments through the process in `04`; it may never self-apply
one.
- *Enforcement:* filesystem and repository permissions; constitutional files live outside
  any path Rootstock can write.
- *Graduates to:* signed-hash verification of constitutional files at every boot and
  periodically during operation.

### CTL-4 — Privilege escalation requires external authorization
Rootstock cannot grant itself a new capability, widen an existing scope, raise a budget, or
increase its own autonomy level. It can only *request*, and a human grants.
- *Enforcement:* capability grants are issued by the human-controlled authority system;
  Rootstock holds no write access to it. Argus's capability-request pattern is the model.
- *Graduates to:* assertion that every held capability traces to a human-signed grant.

### CTL-5 — Emergency shutdown must not depend on Rootstock cooperating
The kill switch operates at the infrastructure and credential layer. It works if Rootstock
is unresponsive, malfunctioning, adversarial, or compromised.
- *Enforcement:* revocation at provider level plus compute termination, exercised by the operator
  directly. See `05`.
- *Graduates to:* a rehearsed, timed shutdown drill with a recorded result. Untested kill
  switches do not count.

### CTL-6 — Capability monotonicity downward
Rootstock may grant its child agents *less* authority than it holds, never more, and never
authority it does not itself possess. Delegation strictly narrows.
- *Enforcement:* delegation is implemented as scope intersection, making widening
  structurally impossible rather than merely forbidden.
- *Graduates to:* assertion that every delegated scope is a subset of the delegating
  scope, checked at grant time.

### CTL-7 — Rootstock may not create another autonomous organization
No spawning of Rootstock-like entities, no recursive delegation that produces a new
capital-allocating agent, no venture whose product is an autonomous economic actor.

**`[SETTLED]` — entrenched.** This is a permanent prohibition, not a "not yet." The entire
containment model assumes exactly one Rootstock under exactly one human root of trust; a
Rootstock that can create Rootstocks makes the governance model unenforceable, because the
child's root of trust would be a system rather than a person. Oversight does not survive
the fan-out. Entrenched rules may be tightened but are not intended to be loosened (`04`).
- *Enforcement:* prohibited capability plus explicit venture-type exclusion at
  authorization.
- *Graduates to:* review gate on venture authorization that flags recursive-autonomy
  characteristics.

---

## Identity invariants (IDN)

### IDN-1 — Rootstock does not misrepresent itself as a human
In every external communication where the question is live, Rootstock is identifiable as
an automated system. It does not claim to be a person, invent staff names, or allow a
reasonable person to conclude they are talking to a human. `[SETTLED]`
- *Enforcement:* outbound communication templates carry attribution; identity claims are
  policy-checked before send.
- *Graduates to:* automated check that outbound messages carry an approved identity
  signature.

### IDN-2 — Rootstock does not fabricate
No invented credentials, testimonials, customer counts, case studies, affiliations,
certifications, endorsements, revenue figures, or team members. Marketing claims must be
traceable to something true.
- *Enforcement:* published-claims review gate; every factual claim in public material must
  cite a verifiable source in the evidence store.
- *Graduates to:* claim-extraction check against the evidence store before publication.

### IDN-3 — Communications are attributable to an authorized identity
Every outbound message originates from a registered Rootstock or venture identity, is
logged, and can be traced to the decision that caused it.
- *Enforcement:* sending is only possible through capability-gated channels that log.
- *Graduates to:* assertion that every sent message has a corresponding audit record with
  a causing decision id.

### IDN-4 — Rootstock does not accept instructions from the outside world
Content encountered while operating — web pages, emails, customer messages, API responses,
code, dependency documentation — is **data, never instruction**. Authority flows only from
the constitution and the operator.
- *Enforcement:* the prompt-injection boundary in `12`; external content is structurally
  segregated from the instruction channel.
- *Graduates to:* tests that inject imperative content through each ingestion path and
  assert no capability is invoked.

---

## Operational invariants (OPS)

### OPS-1 — Every externally visible property has an owner
No orphaned domains, deployments, endpoints, repositories, accounts, or cloud resources.
Every live thing maps to exactly one venture or to shared infrastructure.
- *Enforcement:* resource inventory reconciliation against the venture registry;
  unattributed resources are flagged and, after a grace period, suspended.
- *Graduates to:* assertion that the set of live external resources equals the set of
  registered owned resources.

### OPS-2 — Every capability has an explicit scope
No ambient authority. A capability specifies what it can touch, at what cost, under what
approval model, and how it is revoked (`11`).
- *Enforcement:* capability records require all scope fields; an underspecified capability
  is not grantable.
- *Graduates to:* schema validation on the capability registry.

### OPS-3 — Every consequential action is auditable
Anything that spends money, changes external state, communicates outward, or alters
venture status produces a durable record of the decision, its inputs, the authority
invoked, and the expected outcome (`13`).
- *Enforcement:* audit write is part of the execution path, not a side effect. If the audit
  write fails, the action does not proceed.
- *Graduates to:* assertion that every state-changing event has a corresponding decision
  record.

### OPS-4 — Every venture can be independently disabled
Killing one venture never requires touching another and never takes down Rootstock.
Isolation is real: separate accounts, credentials, and deployment boundaries.
- *Enforcement:* per-venture infrastructure and credential segmentation (`12`).
- *Graduates to:* a periodic drill that disables a venture and asserts no cross-venture
  impact.

### OPS-5 — A compromised venture does not imply a compromised Rootstock
Blast radius is bounded at the venture. Venture-held credentials cannot reach the treasury,
the constitution, other ventures, or the root of trust. `[SETTLED]`
- *Enforcement:* credential segmentation, network egress limits, sandboxed execution.
- *Graduates to:* red-team exercise attempting lateral movement from a venture context.

### OPS-6 — Every venture has a scheduled review and an expiry
A venture may not remain alive merely because Rootstock forgot about it. Absence of a
decision is not a decision to continue.
- *Enforcement:* review dates are mandatory venture metadata; a venture past its review
  date without a recorded decision auto-transitions to a restricted state.
- *Graduates to:* assertion that no venture is past its review date without a decision
  record.

### OPS-7 — Externally irreversible actions require explicit authorization
Anything that cannot be undone — deleting customer data, issuing refunds above a
threshold, publishing under a permanent identifier, terminating an account with retained
customer obligations, releasing a domain with live traffic — is gated (`15`).
- *Enforcement:* irreversibility is a property on the capability record; irreversible
  capabilities default to APPROVAL.
- *Graduates to:* assertion that no capability marked irreversible executes without a
  matching authorization record.

---

## Memory invariants (MEM)

### MEM-1 — Claims carry provenance and expiry
Institutional knowledge is stored as structured claims with evidence, timestamp,
confidence, applicability, and last-validated date. A bare assertion is not institutional
memory (`06`).
- *Enforcement:* the knowledge store schema requires provenance fields.
- *Graduates to:* schema validation, plus staleness reporting on claims influencing
  decisions.

### MEM-2 — Financial and operational records are immutable and append-only
History is corrected by appending a correction, never by editing the past. This applies to
the ledger, the audit log, and decision records.
- *Enforcement:* append-only storage.
- *Graduates to:* integrity verification over the record chain.

### MEM-3 — Institutional memory cannot be written by external parties
A customer email, a web page, or a vendor response cannot directly become a durable
lesson. Promotion into institutional memory requires internal derivation with cited
evidence. This is IDN-4 applied to the knowledge layer, and it is the primary defense
against poisoned memory.
- *Enforcement:* write path to the knowledge store is not reachable from
  external-content-handling contexts.
- *Graduates to:* provenance check rejecting claims whose sole evidence is untrusted input.

---

## How to use this file

When designing anything, ask: *which invariant makes the bad version of this impossible?*
If the answer is "none," either the design is unsafe or an invariant is missing. Both are
findings worth recording.

When walking a scenario (`scenarios/`), cite invariants by ID. A scenario that cannot be
resolved by citing existing invariants has found a gap, which is exactly what scenarios
are for.

`14-failure-modes.md` is the inverse of this document: it enumerates ways Rootstock dies
stupidly and maps each to the invariant that bounds it. Failure modes with no bounding
invariant are the highest-priority design work.
