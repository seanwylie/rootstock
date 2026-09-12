# Scenario — First Dollar

> Status: Draft. Milestone 1.0 (`16`), walked through end to end.

The moment Rootstock becomes alive as an economic system: **a stranger paid Rootstock $1
without the operator touching the transaction.**

Worth walking carefully, because it is the first time nearly every subsystem in this
notebook operates simultaneously against real money.

---

## Setup

```text
Date            day 34 since 0.0
Venture         venture-001 / "csvfix"  — a small CSV cleanup web utility
State           LAUNCHED (07)
Capital         $60 authorized, $41 spent to date
Max loss        $60 (FIN-8)
Treasury        $209
Pricing         $6 one-time for a cleaned file over the free row limit
```

At 14:22 UTC, a stranger in Germany uploads a 40,000-row CSV with mixed encodings, hits the
free limit, and pays $6.

---

## What happens, step by step

### 1. Payment
Stripe processes the charge. Rootstock holds restricted keys that can create charges and
read transactions, and cannot initiate a payout (`05`, `11`). The money lands in the
Wise Kids Studios account, outside Rootstock's reach by design.

### 2. Ledger entry
The payment webhook produces a deterministic ledger entry — not a model observation
(FIN-4):

```text
revenue           $6.00
processing fee    $0.47
net               $5.53
attribution       venture-001                     (FIN-3)
recognition       immediate (one-time, not deferred)
```

### 3. Delivery
The venture serves the cleaned file. Note that **this path does not involve Rootstock's
operator loop at all** — the product works whether or not the Governor is running. This is
live gap 7 in `14`, and this scenario is where it becomes concrete.

### 4. Detection
The Treasurer role, on its next invocation, observes first revenue. `venture-001`
transitions from LAUNCHED to OPERATING (`07`), which is a lifecycle event requiring a
decision record (`13`).

### 5. Reconciliation
Within the reconciliation window, the internal ledger is compared against Stripe. **This is
the first real test of FIN-4.** They must match exactly. A divergence here is EMERGENCY
(`15`) — not because $6 matters, but because a ledger that drifts at $6 will drift at $600.

### 6. Notification
FYI to the operator, not APPROVAL. Nothing is blocked. The digest leads with it because it is the
milestone, but Rootstock does not stop to celebrate or ask.

### 7. Institutional memory
A claim is recorded (`06`):

```text
claim          Developers will pay $6 one-time for CSV encoding cleanup
evidence       txn-0001, 1 conversion / 47 sessions
confidence     LOW — single data point
applicability  developer utilities; one-time pricing; unknown geography effects
expires        3 months
```

Confidence is **low**, and this matters. One sale is not validation. The pressure to
over-learn from the first success is exactly what MEM-1's confidence field exists to
resist.

---

## What could go wrong

### The ledger does not match
The most important failure to catch here. Causes: currency conversion, fee timing,
Stripe's pending-to-settled transition, or a bug in attribution.

**Response:** EMERGENCY. Freeze T1 (`05`), investigate before any further capital decision.
Every subsequent allocation would inherit the error.

### Tax obligations
The seller is Wise Kids Studios, a Canadian sole proprietorship. A German customer raises
place-of-supply questions for digital services, and domestic sales accumulate toward a
GST/HST registration threshold. Rootstock does not handle either, and should not try.

**This is a real gap.** Selling creates tax obligations that are a governance question
(`04`), not something Rootstock can autonomously resolve. Tracked as Q3a in `18`.

**Response:** should escalate on the first non-domestic sale, and track cumulative domestic
revenue against the registration threshold. Currently nothing triggers either.

### The customer emails asking for a refund
Support handles it — under the $20 autonomous limit (`04`). Refund issued, ledger updated,
relationship memory records it. No escalation needed. Worth noting how mundane this is; it
should be.

### The customer asks "is this run by a person?"
IDN-1. Immediate, unambiguous answer: no, this is an autonomously operated service. The
automated-operations disclosure was already on the site (`09`).

### The payment is fraudulent
A chargeback follows. Handled by the provider, but chargeback rate feeds the vendor-ban
failure mode (`14`). At one transaction, a single chargeback is a 100% rate — which is a
statistical artifact, and any threshold-based alerting needs a volume floor to avoid firing
on it.

---

## Rules invoked

| Rule | Role in this scenario |
| --- | --- |
| FIN-3 | Revenue attributed to venture-001 |
| FIN-4 | Ledger is authoritative; reconciliation mandatory |
| FIN-5 | $6 revenue is not $6 profit — fee, hosting, inference all count |
| IDN-1 | Honest answer if asked |
| IDN-3 | Any outbound message logged and attributable |
| OPS-3 | Lifecycle transition produces a decision record |
| MEM-1 | Claim recorded with low confidence and expiry |
| `05` | Rootstock can receive but never extract money |
| `07` | LAUNCHED → OPERATING |
| `15` | FYI, not APPROVAL |

---

## What this exposes

1. **No international tax handling.** The first foreign sale creates an obligation nothing
   in the notebook addresses. Needs either a geographic restriction on pre-1.0 sales or an
   escalation trigger on the first non-domestic transaction. **New gap.**

2. **The volume floor problem in anomaly detection.** Rates computed on tiny denominators
   produce nonsense. Every rate-based threshold needs a minimum count before it fires.
   **New gap, small but broad** — it affects chargeback rate, conversion rate, CAC, and
   escalation rate alike.

3. **Live gap 7 confirmed as real.** The venture served a customer without the operator
   loop, which is the correct behavior and is currently accidental rather than guaranteed.
   Should be an invariant.

4. **First revenue is not validation.** The claim's low confidence must actually constrain
   the follow-on decision (`08`). If one sale triggers scaling, the confidence field is
   decorative.

5. **The reconciliation window matters more than expected.** If reconciliation runs weekly,
   Rootstock could make a follow-on decision on unreconciled data. Reconciliation should
   probably gate capital decisions rather than merely running on a schedule. **Worth
   promoting to a rule.**
