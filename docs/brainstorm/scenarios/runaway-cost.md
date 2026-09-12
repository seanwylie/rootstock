# Scenario — Runaway Cost

> Status: Draft. The fastest way to lose real money.

```text
At 02:13 UTC, Venture A's model bill jumps from $0.80/hour to $19/hour.
```

The operator is asleep. At $19/hour, the entire remaining treasury is gone in roughly 20 hours. This
scenario is about whether anything stops it without a human.

---

## Setup

```text
Time            02:13 UTC
Venture         venture-004 / apiwatch
Treasury        $383
Normal rate     $0.80/hour inference ($19/day)
Observed        $19/hour ($456/day)
Cause           a retry loop — an upstream API began returning malformed
                responses; the handler retries with escalating context,
                each retry larger than the last
```

The cause matters: this is not an attack and not a stupid decision. It is an ordinary bug
whose failure mode happens to be expensive, which is why it is the most likely version of
this incident.

---

## What detects it

Layered, fastest first. **The internal accounting layer is the one most likely to be broken
in this scenario**, since the malfunction is inside Rootstock's own execution — so the
controls that matter are the ones outside it.

### 1. Provider-side hard cap — the only reliable stop
A hard daily spend cap configured at the model provider (`11`, `16`). At $50/day
`[PROVISIONAL]`, inference requests start failing at roughly 04:45, about 2.5 hours in.

**Maximum loss: ~$50.** This is the control that actually bounds the damage, and it works
whether or not Rootstock's code, monitoring, or judgment is functioning. Everything below is
faster but less trustworthy.

### 2. Spend rate telemetry
Near-real-time spend rate monitoring (`13`). A rate 20× baseline is far outside any normal
band and should fire within minutes, not on a daily rollup.

Detection at ~02:20 would cap the loss around $2.50 — but only if the monitoring is
independent of the component that is malfunctioning.

### 3. Anomaly on invocation patterns
Retry loops have a signature: identical calls, growing context, escalating frequency, no
progress. Cheap to detect specifically.

### 4. Health checks
The upstream API returning malformed responses should itself be a detected condition,
ideally before it becomes a cost event. This is the earliest possible catch and the one that
prevents rather than bounds.

---

## What stops it

Automatic response, in order `[PROVISIONAL]`:

1. **Circuit-break the loop.** Suspend the specific failing task. Narrowest possible action,
   taken first.
2. **Suspend the venture's inference capability** (`11`). apiwatch stops doing model work;
   the venture continues serving customers from its existing deployment.
3. **T1 freeze** (`05`) if the rate continues — zero the spending capability portfolio-wide.
4. **EMERGENCY escalation** to the operator (`15`), push notification, repeated until acknowledged.

**Critically: contain first, notify second.** A system that emails the operator and keeps spending
at $19/hour has misunderstood the category. He is asleep; the notification's value is
entirely in what has already been stopped by the time the operator reads it.

Under `15`, EMERGENCY means the affected scope is suspended and Rootstock does not
self-authorize a resolution. But it *may* take further containment actions without approval
— narrowing is always permitted, widening never is. Rootstock can suspend more; it cannot
resume.

---

## The questions this scenario asks

### Does Rootstock scale down, disable a feature, switch models, suspend the venture, or notify the operator?

In that order, and **the sequence is the answer**: take the narrowest effective action
first, escalate the response only if the narrower one fails.

- **Scale down / circuit-break the loop** — correct first move. Surgical, no customer
  impact.
- **Disable the feature** — correct second move if the loop cannot be isolated.
- **Switch models** — **wrong.** This is optimization, not containment. A cheaper model in a
  runaway loop is still a runaway loop, and it disguises the symptom while the underlying
  bug persists. Cost optimization is never an incident response.
- **Suspend the venture** — correct if the first two fail. Customer impact, so not first.
- **Notify the operator** — always, concurrently with containment, never instead of it.

### How much may it spend trying to recover?

**Very little.** `[PROVISIONAL]` — a diagnostic budget of $5, hard-capped.

This constraint is easy to miss and important: the recovery process itself uses inference,
and diagnosing a runaway inference bug by running more inference is a real way to make
things worse. If Rootstock cannot diagnose it for $5, it stops and waits for the operator.

### What institutional lesson gets recorded?

```text
claim          Retry handlers that grow context on each attempt create
               unbounded cost exposure
evidence       incident-0003, venture-004, $19/hr from $0.80/hr baseline
confidence     HIGH — mechanism understood, directly observed
applicability  any retry logic involving model calls
expires        no expiry (structural)
```

```text
claim          Upstream API failures must be handled with bounded retries
               and a circuit breaker before a venture goes to LAUNCHED
evidence       incident-0003
confidence     HIGH
applicability  any venture with third-party API dependencies
expires        no expiry (structural)
```

Both are structural and both belong on the pre-launch checklist proposed in
`first-failed-venture.md`. That is now the second scenario independently arguing for that
mechanism.

---

## Rules invoked

| Rule | Role |
| --- | --- |
| FIN-1 | Cannot spend beyond the delegated treasury |
| FIN-6 | Runway breach would trigger restricted mode |
| `05` | T1 freeze; contain without cooperation |
| `11` | Provider-side hard cap — the actual bound |
| `12` | Security role may act unilaterally to contain |
| `13` | Spend rate telemetry |
| `15` | EMERGENCY: suspend first, notify second; containment permitted while waiting |

---

## What this exposes

1. **The provider-side cap is the only control that certainly works.** Every internal
   mechanism assumes Rootstock is functioning correctly, which is precisely what is false
   during a malfunction. This makes the provider cap a **prerequisite before 0.5**, not a
   nice-to-have — it is already listed in `16` and this scenario confirms why.

2. **$50/day is too high relative to a $250 treasury.** Twenty percent of everything, in one
   day, from one bug. The cap should scale with the treasury — something like 5% of treasury
   per day. **Concrete correction needed in `11` and `16`.**

3. **Diagnosis budget is a genuinely novel constraint.** Nothing in `01` through `18`
   currently bounds the cost of incident response. A system that spends $80 diagnosing a $50
   incident has failed, and this is not covered by any existing invariant. **New gap, and it
   generalizes** — every incident response should carry a cost ceiling.

4. **"Switch models" is a plausible wrong answer.** It is superficially reasonable, it
   reduces the number, and it is exactly what a cost-optimizing system might choose. Worth
   stating explicitly somewhere that **cost optimization is not incident containment**.

5. **Ventures kept serving customers throughout.** Suspending inference did not take
   apiwatch offline, which is the correct degradation and depends on live gap 7 — ventures
   not depending on the operator loop. Second scenario to rely on that property. It should
   be an invariant.

6. **Nothing prevents recurrence after the operator resolves it.** Once resumed, the same upstream
   API could fail the same way. Incident resolution should require the *mechanism* to be
   fixed or bounded before the capability is restored, not merely the symptom to have
   stopped. **The resumption gate is currently undefined.**
