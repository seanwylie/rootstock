# 11 — Tools and Capabilities

> Status: Draft.

This document inventories **capability classes rather than vendors**. Vendors change;
capability classes are stable, and the risk analysis attaches to the class. "Rootstock can
send email" is a durable statement about power. "Rootstock uses the Gmail API" is an
implementation note.

The capability is the unit of trust. Per Principle 2, Rootstock's power comes entirely from
this inventory — not from the model.

## The capability record

Every capability is declared with all of these fields. An underspecified capability is not
grantable (OPS-2).

```text
id                 comms.email.send
description        Send email from an authorized Rootstock or venture identity
scope              specific sending identities; recipients who have interacted;
                   volume cap of N/day
risk_class         medium
cost_model         negligible per message; reputational cost on misuse
credential_type    OAuth, scoped to send-only, no mailbox admin
approval_model     L3 within scope; L0 for new sending identities
reversibility      irreversible once sent
auditability       full message log with causing decision id (IDN-3)
revocability       immediate, at provider level
blast_radius       venture identity reputation; domain reputation if abused
depends_on         identity.workspace
```

The fields that get skipped and shouldn't:

- **Reversibility** drives the default approval model. Irreversible capabilities default to
  APPROVAL (OPS-7).
- **Blast radius** is what turns an incident into a bounded incident. If the answer is
  "everything," the capability is scoped wrong.
- **Depends_on** exposes chains. A capability that looks low-risk but depends on a
  high-risk one inherits that risk, and these chains are how privilege quietly accumulates.

## Risk classes

`[PROVISIONAL]`

| Class | Definition | Default treatment |
| --- | --- | --- |
| **Low** | Reversible, cheap, no external visibility | L4, logged |
| **Medium** | Externally visible or costs money within caps | L3, logged, capped |
| **High** | Irreversible, expensive, or affects customers | L2 with hard caps, or L1 |
| **Critical** | Touches money movement, identity, or the trust root | L0 or prohibited |

## The inventory

### COMMUNICATION

| Capability | Risk | Notes |
| --- | --- | --- |
| Send email | Medium | Authorized identities only (IDN-3); volume-capped; irreversible |
| Receive email | Medium | **Untrusted input** — primary injection vector (`12`) |
| Support ticketing | Medium | Bound by commitment limits (`04`) |
| SMS | High | Regulated, expensive, high abuse potential. Not before 1.0 `[PROVISIONAL]` |
| Publish to owned web property | Medium | Claim-checked (IDN-2) |

### COMPUTE

| Capability | Risk | Notes |
| --- | --- | --- |
| Provision infrastructure | High | Per-resource-class cost caps; runaway cost is a named failure mode |
| Deploy | Medium | Venture-scoped; reversible via rollback |
| Modify configuration | Medium | Version-controlled, revertible |
| Inspect logs | Low | May contain PII — access is itself scoped |
| Execute code | High | Sandboxed always (`12`) |
| Destroy infrastructure | High | Irreversible if data-bearing; gated |

The cost cap on provisioning must be **provider-enforced, not application-enforced**. A
budget check in Rootstock's own code does not survive Rootstock's own code being wrong,
which is precisely the scenario where it matters.

### COMMERCE

| Capability | Risk | Notes |
| --- | --- | --- |
| Receive payment | Medium | The point of the exercise |
| Create/modify subscription | High | Affects recurring customer obligations |
| Issue refund | High | Money out; capped at $20 autonomous `[PROVISIONAL]` |
| Read transactions | Low | Feeds the ledger |
| Change pricing | Medium | Floor and ceiling are constitutional |
| **Move money out / payout** | **Prohibited** | Never held by Rootstock (`05`) |

The prohibition on payouts is the single most important line in this inventory. It bounds
the worst financial outcome of total compromise to *wasted* capital rather than *stolen*
capital.

### IDENTITY

| Capability | Risk | Notes |
| --- | --- | --- |
| Register domain | Medium | Approved TLD list; cost-capped |
| Manage DNS in delegated zone | Medium | Zone-scoped, not registrar-level (`05`) |
| Registrar account access | **Prohibited** | Root of trust |
| Create Workspace user | High | Identity creation. L0 |
| Workspace super-admin | **Prohibited** | Root of trust |
| Manage OAuth for owned apps | High | Credential issuance |

### RESEARCH

| Capability | Risk | Notes |
| --- | --- | --- |
| Web fetch / search | Low cost, **high injection risk** | Content is data, never instruction (IDN-4) |
| Analytics read | Low | Own properties |
| Competitive research | Low | Public sources; snapshot with fetch date |
| Purchase data / reports | Medium | Spend-gated; licensing terms matter |

Web research is the clearest case where **cost risk and security risk diverge sharply**. It
is nearly free and one of the two main injection vectors. Risk class should arguably be a
pair rather than a single value.

### DEVELOPMENT

| Capability | Risk | Notes |
| --- | --- | --- |
| Repository read/write | Low | Own repos |
| Create repository | Low | Within the org |
| CI/CD execution | Medium | Runs code; sandboxed; holds secrets |
| Install dependencies | **High** | Supply chain. Third-party code executing with venture privileges |
| Issue tracking | Low | |
| Merge to production branch | Medium | Gated by checks, not by judgment |

**Dependency installation is the most underrated risk here.** It is routine, constant, and
executes arbitrary third-party code inside a venture context. Mitigations: lockfiles,
scanning, and the OPS-5 assumption that a compromised venture must not imply a compromised
Rootstock.

### MODEL ACCESS

| Capability | Risk | Notes |
| --- | --- | --- |
| Inference | Medium (cost) | Largest controllable cost; hard daily cap |
| Model selection | Low | See `18` — can Rootstock choose to spend more on better models? |
| Fine-tuning / training | Prohibited during bootstrap | Cost and unclear value `[PROVISIONAL]` |

Inference needs a **provider-side hard cap**, not just internal accounting. A runaway loop
is a plausible failure and the internal counter is exactly what would be broken in that
scenario.

## Cross-cutting rules

1. **No ambient authority** (OPS-2). Every capability is explicitly granted and scoped.
2. **Delegation narrows** (CTL-6). A role or venture receives a subset, never a superset.
3. **Every use is logged with a causing decision id** (OPS-3).
4. **Revocation is immediate and does not require cooperation** (CTL-5).
5. **Credentials are venture-scoped** where the capability is venture-specific (OPS-5).
6. **Capabilities have owners** — exactly one role is accountable for each.
7. **Unused capabilities are revoked.** `[PROVISIONAL]` A capability unused for 90 days is
   flagged and removed. Standing authority nobody uses is pure attack surface.

## Capability requests

When Rootstock needs something it does not hold, it cannot take it (CTL-4). It files a
request — the Argus `capability request` pattern, which already exists as a first-class
concept there and should be reused.

```text
capability     commerce.refund above $20
why            three refund requests in two weeks exceeded the limit,
               each waiting on approval, harming support responsiveness
evidence       ticket ids, delays incurred
scope wanted   up to $50, venture-002 only
risk           maximum $50 additional exposure per incident
alternative    keep escalating; slower but safe
```

Two things this gets right: requests are **evidence-driven** rather than speculative, and
they name the alternative, which makes refusal a real option rather than an obstruction.

A steady stream of capability requests is a healthy signal — it means Rootstock is hitting
real boundaries and articulating them. Silence means either everything is granted or
Rootstock has stopped trying.

## Relationship to Argus enforcement

Argus's Phase 1 permission keys (`observe_prod_signals`, `mutate_nonprod`, `mutate_prod`,
`commit_local`, `push_remote`, `deploy`, `change_experiments`, `builder_execute`) with
`yes` / `no` / `confirm` values, evaluated deterministically before execution, are a
working implementation of much of this document's development and compute sections.

Rootstock's inventory is broader — Argus has no commerce, communication, or identity
capabilities because it never talks to customers or spends money. But the enforcement
*shape* is right and worth adopting rather than reinventing: declarative per-scope YAML, a
deterministic evaluator, a gate ahead of execution, and an artifact recording the decision.

## Open questions

- Should risk class be a single value or a vector? Web research is low-cost and
  high-injection-risk; the single value loses that.
- How are capabilities versioned? A capability whose scope changes is arguably a new
  capability, and grants should not silently follow a redefinition.
- Should there be a "capability budget" — a cap on how many capabilities Rootstock holds
  simultaneously, forcing trade-offs? Interesting, possibly artificial.
- How does a capability get retired when a venture is archived? Should be automatic as part
  of teardown (`07`), and it is exactly the kind of thing that gets missed.
