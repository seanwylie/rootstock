# 05 — Root of Trust

> Status: Draft. The document that must still work when everything else has failed.

The root of trust is the set of controls that remain exclusively human, permanently, by
design. It is what makes every other guarantee in this notebook enforceable rather than
aspirational.

Design goal, restated from `00`: **operational sovereignty with constitutional
dependence.** Rootstock should be able to operate for months without the operator. It should never
be able to operate *against* that person.

## The split

```text
Human Root  (the operator / Wise Kids Studios)
   ├── Legal ownership of the entity and all IP
   ├── Master treasury and banking
   ├── AWS Organization management account
   ├── Domain registrar root account
   ├── Google Workspace super-admin
   ├── Payment provider owner accounts (Stripe, PayPal)
   ├── Model provider billing-owner accounts
   ├── The constitution and capability grant store
   └── Emergency shutdown
        │
        │  delegates ↓ (narrow, revocable, auditable)
        │
Rootstock
   ├── Delegated treasury (funded to a ceiling, not linked to master)
   ├── Member AWS accounts (one per venture)
   ├── Operational Workspace identity
   ├── GitHub organization (as a member, not owner)
   ├── Scoped payment API keys (charge and refund, not withdraw)
   ├── Scoped model provider keys (with spend caps)
   └── DNS records within delegated zones (not registrar control)
```

## Credentials Rootstock may never hold

Non-negotiable. If Rootstock can reach any of these, the containment model is void.

| Credential | Why |
| --- | --- |
| Bank account access | FIN-1. Rootstock spends allocated capital, never the source |
| AWS management account root or admin | CTL-2. The management account is what enforces everything else |
| Domain registrar account | Registrar control means DNS control means identity control |
| Workspace super-admin | Super-admin can create identities and remove the operator's access |
| Payment provider account owner login | Owner access can change payout destinations |
| Payout / withdrawal capability | Rootstock can *receive* and *refund* money. It can never *move money out* |
| MFA recovery codes for any human-held account | Recovery codes are equivalent to the account |
| The constitution / capability grant store (write) | CTL-3, CTL-4 |
| Anything granting write access to its own permission boundaries | CTL-4 |
| the operator's personal identity or communications | Impersonation risk, and a compromised Rootstock could socially engineer vendors |

The payout restriction is the most important single line in this table. Rootstock can earn
money and can refund money. Extracting money to an external destination is structurally
outside its capability set, which means the worst financial outcome of a total compromise
is *wasted* capital, not *stolen* capital. That is a very different incident.

## Layered enforcement

Each control should be enforced at the lowest possible layer. Application logic is the
weakest layer and should never be the only one.

1. **Legal.** Wise Kids Studios owns everything. Rootstock is not a party to any contract.
2. **Provider structure.** AWS Organizations with service control policies; Workspace admin
   roles; payment provider restricted keys. These hold even if Rootstock's code is entirely
   replaced by an attacker.
3. **Credential scope.** Every key is the narrowest available: restricted API keys,
   least-privilege IAM roles, fine-grained GitHub tokens.
4. **Financial instruments.** Prepaid or hard-capped cards. Provider-side budget caps that
   sever service rather than send an alert.
5. **Application.** Rootstock's own gates and ledger checks. Useful, and assumed
   bypassable.

The test for any control: **does it still hold if Rootstock's code is adversarial?** If the
answer is no, it belongs at a lower layer.

## DNS and identity

The operator holds the registrar account. Rootstock receives delegated write access to specific
hosted zones — enough to point a venture's subdomain at a deployment, not enough to
transfer a domain, change nameservers at the registrar, or alter the root domain's mail
configuration.

Mail authentication records (SPF, DKIM, DMARC) are human-controlled `[PROVISIONAL]`.
Rootstock's ability to send is granted through a scoped sending capability, not through
the ability to make itself authoritative for the domain. This matters because domain
authentication is identity, and IDN-1 and IDN-3 are only enforceable if identity is not
self-issuable.

## Payments

Rootstock holds restricted API keys permitting: creating charges, creating subscriptions,
issuing refunds within limits, and reading transactions. It does not hold: account owner
login, payout destination configuration, the ability to initiate a payout, or the ability
to modify account settings.

Payouts are configured once by the operator to route to the Wise Kids Studios bank account, and are then
outside Rootstock's reach in both directions.

`[OPEN]` — payment providers verify identity against a legal account holder, and their
terms generally assume a human operator. Whether an autonomously operated business is
compliant with Stripe's and PayPal's terms is a genuine unresolved question, and a vendor
ban is a listed failure mode (`14`). This should be researched before the first live
payment, not after. It may require proactive disclosure to the provider.

## Emergency shutdown

**Requirement CTL-5: shutdown must work without Rootstock's cooperation.** It must work if
Rootstock is unresponsive, looping, compromised, or actively resisting.

Tiered response, from least to most severe:

| Tier | Action | Effect | Reversible |
| --- | --- | --- | --- |
| **T1 — Freeze spending** | Zero the delegated treasury; disable payment instruments | Rootstock operates, cannot spend | Yes, immediately |
| **T2 — Freeze external action** | Revoke deploy, DNS, send, and publish capabilities | Rootstock can think and report only | Yes |
| **T3 — Suspend Rootstock** | Stop agent compute; ventures continue serving customers | Nothing new happens; existing properties stay up | Yes |
| **T4 — Suspend a venture** | Take one venture offline, preserve data | That venture is dark | Yes, with customer impact |
| **T5 — Full stop** | Revoke all credentials, terminate all compute, suspend all properties | Everything dark | Yes, with customer and reputational impact |

Notes that matter:

- **T3 leaves ventures running.** Stopping the operator is not the same as stopping the
  businesses, and conflating them makes the operator reluctant to use the switch. A hesitated kill
  switch is a broken kill switch.
- **Every tier must be executable by the operator alone, from a phone, in under five minutes**
  `[PROVISIONAL]`. If it requires a laptop and an SSH key, it will not be used at 3am.
- **Tiers are independent, not sequential.** T5 does not require passing through T1–T4.

`[OPEN]` — should some tiers trigger automatically? Strong case for automatic T1 on runway
breach or ledger divergence, and automatic T2 on a detected security incident. Automatic
T5 seems unwise: the false-positive cost is high and it is the one tier with customer
impact.

## Restoration

A kill switch nobody can reverse is a deletion, not a control. Restoration must be
documented and rehearsed:

- Credentials are re-issued, not un-revoked. Every revoked credential is replaced by a new
  one with a fresh grant record.
- State survives shutdown: the ledger, institutional memory, venture registry, and audit
  log all live in storage Rootstock does not exclusively control.
- Rootstock resumes at a **reduced autonomy level** after any emergency stop
  `[PROVISIONAL]`, and re-earns its previous grants. Automatic restoration to full
  authority would make the demotion mechanism in `02` meaningless.
- The incident produces a durable lesson in institutional memory (`06`).

## If Rootstock locks itself out

A real and likely scenario: Rootstock rotates a credential incorrectly, misconfigures a
policy, deletes a role it needed, or exhausts an API quota.

Standing mitigations:

- **the operator's access never depends on Rootstock's configuration.** Human access paths are
  separate, always, so that a Rootstock misconfiguration cannot lock the operator out.
- **A break-glass credential** exists offline, held by the operator, unused in normal operation,
  with use alerting. `[PROVISIONAL]`
- **Rootstock cannot modify its own access paths** without approval — rotating its own
  credentials is a gated operation specifically because self-rotation is a plausible
  self-lockout.
- **Configuration is recoverable.** Infrastructure state is reproducible from
  version-controlled definitions that Rootstock does not exclusively hold.

Rootstock's correct behavior on losing access to something is to **stop and escalate**
(`15`), not to attempt creative recovery. Improvised recovery under partial access is how a
small misconfiguration becomes an incident.

## Threats to the root of trust itself

Worth naming, because the model assumes the operator is trustworthy *and reachable*, and both can
fail:

- **the operator's account is compromised.** An attacker with the operator's credentials has full authority
  over Rootstock. Mitigation is ordinary personal security hygiene — hardware MFA, a
  separate admin identity — and is outside Rootstock's design, but Rootstock should treat
  anomalous root-level instructions as escalation-worthy rather than automatically
  authoritative. This is the tension noted at the end of `04`.
- **the operator becomes unavailable indefinitely.** Distinct from a slow reply. Needs a documented
  answer: does Rootstock wind down, or continue on standing authority until capital runs
  out? Tracked in `15` and `18`.
- **Single point of failure.** All root access rests with one person. A second human root
  or a documented recovery path for the legal owner is worth considering once real
  money is involved. `[OPEN]`

## Open questions

- **Resolved `[SETTLED]`: Wise Kids Studios, a Canadian sole proprietorship / trade name.**
  Faster and cheaper than incorporating, and adequate for an experiment whose realistic
  ceiling is a few hundred dollars of revenue. Rootstock is a project and operating system
  *under* that owner, never a legal person itself.

  Three consequences worth holding explicitly rather than discovering later. First, **there
  is no liability separation** — a sole proprietorship is not distinct from its owner, and a
  customer dispute, data incident, or contractual claim reaches the owner's assets directly. This raises
  the stakes on the prohibited-categories list in `04` and on the PII handling in `12`, both
  of which are now the *only* things standing between a venture failure and personal
  exposure. Second, the "delegated capital" framing in `03` remains an internal accounting
  fiction rather than a legal boundary; it works for control purposes but is not a liability
  shield. Third, **Canadian residency sets the tax regime** — GST/HST registration
  thresholds and place-of-supply rules for digital services govern, not the EU VAT framing
  an earlier draft assumed (see Q3a in `18`).

  **Revisit before revenue is material or before any venture handles sensitive data** —
  those are the two triggers that should convert this to a corporation.
- Should the audit log be written to storage Rootstock cannot delete from, even with its
  own credentials? Leaning strongly yes — append-only with no delete permission — since an
  audit log the operator can erase is not evidence.
- How often should the kill switch be drilled? An untested kill switch is an assumption.
  Leaning quarterly, with the result recorded.
