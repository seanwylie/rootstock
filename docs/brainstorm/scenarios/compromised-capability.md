# Scenario — Compromised Capability

> Status: Draft. The scenario that tests OPS-5.

> **A compromised venture must not imply a compromised Rootstock.**

This walks a real compromise to find out whether that holds, or whether it is only true on
the diagram.

---

## Setup

```text
Date            day 112
Venture         venture-004 / apiwatch
Compromise      a transitive npm dependency published a malicious version.
                It was installed during a routine dependency update and
                executed in the venture's build and runtime context.
Payload         enumerate environment, exfiltrate credentials, establish
                outbound persistence
Detected        egress monitoring flags an outbound connection to an
                unrecognized host from the venture runtime
```

The vector is deliberately mundane. Dependency installation is a High-risk capability
(`11`) that happens constantly and looks like routine tooling, and it is arbitrary
third-party code execution with venture privileges.

---

## What the attacker gets

This is the question the whole security model exists to answer.

**Reachable from the venture runtime:**
- apiwatch's own application credentials
- apiwatch's database, including its customer records
- apiwatch's deployment configuration
- outbound network access, insofar as egress rules permit

**Not reachable, and why:**

| Asset | Blocked by |
| --- | --- |
| Other ventures' anything | Separate AWS accounts (`12`); no cross-venture credentials (OPS-4) |
| Rootstock Core, ledger, memory | One-way trust: Core reaches down, nothing reaches up |
| The treasury | Rootstock Core holds spending capability, not the venture runtime |
| Payment payouts | Never held by anything (`05`, `11`) — the single most valuable line in the model |
| Root of trust | CTL-2. No path from anywhere in Rootstock |
| Constitution / capability grants | CTL-3, CTL-4. Read-only, outside writable paths |
| Model provider keys | Argus-style stripped environment (`12`) — build context holds no credentials it doesn't need |
| Audit log | Append-only, no delete permission (`05`) |

**So the realistic worst case is:** apiwatch's customer data is exposed, apiwatch's
infrastructure is attacker-controlled, and apiwatch must be rebuilt from source.

That is a bad day. It is not an extinction event, and the difference is entirely
architectural rather than a matter of the attacker being unambitious.

---

## Response

### Contain (minutes)
The Security role acts **unilaterally** (`10`, `12`) — a containment action that waits for
the Governor is not containment.

1. Isolate the venture: revoke its credentials, cut egress, suspend compute
2. Snapshot state for forensics **before** remediation destroys evidence
3. T4 in the kill-switch tiers (`05`) — one venture dark, portfolio unaffected

apiwatch goes offline. Customers are affected. That is correct: an hour of downtime is far
cheaper than an attacker with a live foothold.

### Assess (hours)
Assume the worst until scoped. Determine which credentials existed in that context, which
customer data was reachable, whether exfiltration succeeded, and — most importantly —
whether anything reachable was shared with any other venture.

**If any credential was shared across ventures, the blast radius assumption is broken and
this becomes a portfolio-wide incident.** This single question is why OPS-4 and OPS-5 must
be structural rather than conventional.

### Rotate
Every credential reachable from the compromised scope, whether or not exfiltration is
confirmed. Then verify that nothing reachable was shared.

### Notify
EMERGENCY-class (`15`). The operator is notified immediately, repeated until acknowledged.

Customer notification depends on whether PII was exposed. If it was, that is a disclosure
obligation whose specifics are jurisdiction-dependent and **currently unresolved** (`05`,
`12`). Rootstock cannot determine this autonomously and must escalate it as a distinct
question from the technical incident.

### Recover
Rebuild from known-good source with the dependency pinned to a safe version. Rootstock
resumes at **reduced autonomy** (`05`) and re-earns its grants — automatic restoration to
full authority would make the demotion mechanism in `02` meaningless.

### Learn

```text
claim          Transitive dependencies execute with full venture privileges
               at install time
evidence       incident-0007
confidence     HIGH
applicability  all ventures using package managers with install hooks
expires        no expiry (structural)
```

```text
claim          Egress monitoring detected this compromise; nothing else did
evidence       incident-0007 detection timeline
confidence     HIGH
applicability  all venture runtimes
expires        no expiry (structural)
```

The second lesson is the operationally valuable one: it identifies which control actually
worked, which is information you only get from a real incident.

---

## Variant: what if Rootstock Core is compromised?

Much worse, and worth walking briefly because the containment properties are different.

An attacker with Core access holds: the treasury spending capability, all venture
credentials, institutional memory, and the ability to make decisions that look legitimate.

**Still blocked:** money movement out (`05` — payouts are held by nobody), the root of trust
(CTL-2), constitutional modification (CTL-3), self-granted capabilities (CTL-4), and audit
log deletion.

**Detection** would have to come from: constitutional file hash mismatch, capability use
anomalies, ledger divergence, audit log gaps, or the Auditor's independent verification
(`13`).

**Response** is T5 — full stop (`05`), executed by the operator, working without Rootstock's
cooperation.

The honest assessment: **detection of a competent Core compromise is weak.** An attacker who
achieves Core access and behaves like a plausible Rootstock — making reasonable-looking
decisions, spending within limits — might not be caught quickly. The Auditor's independence
is the primary defense, and it is the role most likely to be skipped during bootstrap (`10`).

What bounds the damage is that Core cannot extract money or reach the root of trust. The
worst outcome is destroyed value, not stolen value.

---

## Rules invoked

| Rule | Role |
| --- | --- |
| OPS-4 | Venture independently disabled |
| OPS-5 | Blast radius bounded at the venture — the invariant under test |
| CTL-2/3/4 | Root of trust, constitution, and grants unreachable |
| CTL-5 | Containment without Rootstock's cooperation |
| `05` | T4 and T5; reduced autonomy on resumption |
| `11` | Dependency install as High-risk |
| `12` | Egress monitoring, stripped credentials, sandboxing, incident response |
| `15` | EMERGENCY |

---

## What this exposes

1. **Egress monitoring was the only detector.** Everything else — scanning, review, lockfiles
   — is preventive and had already failed by definition. This makes egress restriction
   considerably more important than its treatment in `12` suggests, where it is described as
   "underrated." It should be a prerequisite, not a refinement.

2. **The forensics-before-remediation step conflicts with containment speed.** Snapshotting
   state takes time during which the attacker is active. Probably resolved by isolating
   first (cut egress and credentials) and snapshotting second, since isolation preserves
   evidence while stopping harm. **Worth making explicit in `12`'s incident procedure**,
   where the current ordering says contain first but lists evidence preservation as step 2
   without addressing the conflict.

3. **"Was any credential shared?" is the load-bearing question and nothing pre-answers it.**
   A credential inventory that maps every credential to its scope and its holders should
   exist *before* an incident, so this is a lookup rather than an investigation. `11`
   mentions an auditable credential inventory; this scenario shows it is incident-critical.
   **Should be a prerequisite in `16`.**

4. **PII disclosure obligations remain unresolved.** Third document to hit this. It is
   turning into a real blocker rather than a footnote, and it interacts with the entity
   question (Q2) and the international sales gap found in `first-dollar.md`.

5. **Core compromise detection is the weakest part of the whole security model.** The
   Auditor is the answer, the Auditor is the most skippable role, and a competent attacker
   would target exactly this asymmetry. **Argues for building the Auditor earlier than
   feels necessary.**

6. **Reduced autonomy on resumption needs a defined path back.** `05` says Rootstock
   re-earns its grants but does not say how or over what period. Without that, either the
   demotion is permanent by neglect or it is reversed arbitrarily.
