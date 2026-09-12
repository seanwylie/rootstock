# 02 — Capability Model

> **Status: Decided.** This document is normative.

## The central claim

**Rootstock never "has AWS."** It never has a cloud account, an API key, or a permission.
It has a set of named capabilities, each individually granted, scoped, priced, logged, and
revocable.

```text
sandbox.s3.create_bucket
sandbox.lambda.deploy
sandbox.logs.read
web.search
memory.read
memory.write
```

That list is the vocabulary of Rootstock's autonomy. Nothing outside it is possible, and
growing it is a deliberate human act. When someone asks "what can Rootstock do?", the honest
and complete answer is an enumeration of granted capabilities — not a description of a
model's abilities.

This is the operative form of *autonomy is granted through capabilities, not assumed through
intelligence.*

## The pipeline

```text
CapabilityRequest
{
    actor
    capability
    target
    parameters
    estimated_cost
    justification
}
        │
        ▼
   Policy Engine          deterministic, out of process (AR-3)
        │
        ▼
ALLOW │ DENY │ REQUIRE_APPROVAL
        │
        ▼
    Executor              holds credentials; model never does (AR-12)
        │
        ▼
CapabilityResult
{
    outcome
    actual_cost
    artifacts
    audit_id
}
```

Four properties this shape buys, each of which is hard to retrofit:

- **The model proposes and never executes.** A `CapabilityRequest` is inert. It is data,
  and it can be logged, replayed, tested, and refused.
- **Authorization is separable from reasoning.** The policy engine can be tested against
  a corpus of requests with no model involved.
- **Cost is estimated before and measured after.** The gap between `estimated_cost` and
  `actual_cost` is a calibration signal and the primary early warning for runaway spend.
- **Every result carries an `audit_id`.** There is no path to a side effect that does not
  produce a record (AR-4).

## CapabilityRequest

```text
schema_version    1                        versioned; unknown versions rejected
idempotency_key   cycle number or task id  stable across retries of the same intent
actor             role or task identity making the request
capability        sandbox.s3.create_bucket declared id only, never free-form (AR-16)
target            the specific resource or scope acted upon
parameters        capability-specific, schema-constrained
estimated_cost    { usd: 0.00, tokens: 0 }
justification     why, in one or two sentences
decision_ref      the decision record this serves
provenance        trusted | derived_from_untrusted     (AR-11)
```

**There is no caller-supplied request id.** The broker derives a canonical id by hashing the
idempotency key together with the request content, and deduplicates on that
(`03-runtime-and-broker.md`). An opaque id chosen by the caller could be varied — by a retry
bug or deliberately — to slip past deduplication. A derived id makes two logically identical
requests collide by construction.

**`capability` names a declared id and nothing else.** The broker has no generic dispatch
path, so an undeclared id is unroutable rather than merely denied. This is AR-16, and it is
what separates a capability broker from a privileged proxy: `sandbox.s3.create_bucket` with a
constrained schema is a capability; `aws.call(service, operation, params)` would preserve
every process boundary while handing the caller an AWS shell.

Two more fields deserve comment.

**`provenance`** marks whether this request was formulated in a context that had handled
untrusted external input — a customer email, a fetched web page. Requests marked
`derived_from_untrusted` are subject to stricter policy regardless of capability, which is
how AR-11 is enforced mechanically rather than by vigilance. A refund request that arose
while reading a customer email is not the same as one that arose from a scheduled review,
even if the parameters are identical.

**`estimated_cost`** is mandatory and may be zero. Requiring the actor to state a cost
before acting is cheap, and the estimate-versus-actual comparison is one of the few
genuinely predictive signals available.

## Policy engine

Deterministic. Runs out of process from the model. Same inputs always produce the same
decision (AR-3).

At broker ingress, **schema validation** (AR-16) happens before anything else. Unknown
`schema_version`, undeclared capability id, or parameters failing the capability's declared
schema → rejected. Malformed input never reaches policy code.

**Policy evaluation precedes claiming** (F-1). A lease means execution is in flight.
`REQUIRE_APPROVAL` is written to the approval store and never occupies `PENDING`. After
ALLOW, the broker claims (AR-15) so a replayed allowed request cannot execute twice.

A cheap existence lookup on the claim and approval tables may still run before policy so a
replay consumes no budget. That lookup must not take a lease.

Evaluation is then ordered, and **the first DENY wins**. Ordering cheapest and most absolute
checks first means the common rejection path involves no I/O:

1. **Is the capability granted at all?** Declared but ungranted → DENY. Declaration and
   grant are separate: a capability can exist in the vocabulary and be available to nobody.
2. **Is it granted to this actor?** Not in the actor's grant set → DENY.
3. **Is it within scope?** Target outside the granted scope → DENY. Scope is intersected,
   never widened (AR-7).
4. **Is it constitutionally prohibited?** Some capabilities can never be granted; check
   independently of grants so a bad grant cannot enable one.
5. **Provenance check.** If `derived_from_untrusted`, apply the restricted table.
6. **Budget check.** Would `estimated_cost` breach a cap? → DENY. Deterministic ledger read
   (AR-5).
7. **Rate and quota check.** Invocation frequency, aggregate daily cost, aggregate refund
   totals.
8. **Autonomy level.** L0 → REQUIRE_APPROVAL. L1 → REQUIRE_APPROVAL unless a standing grant
   covers it. L2+ → ALLOW within envelope.
9. **Irreversibility.** Irreversible and not explicitly pre-authorized →
   REQUIRE_APPROVAL.

Output:

```text
decision          ALLOW | DENY | REQUIRE_APPROVAL
decision_id       dec_01J8...
rule              the specific rule that determined the outcome
scope_granted     the intersected scope the executor may use
cost_ceiling      hard ceiling; executor aborts if exceeded
expires_at        decisions are short-lived
```

`rule` matters more than it looks. "DENY" is nearly useless for debugging; "DENY by
`budget.sandbox.daily`" tells Rootstock what to do differently, and lets it file a coherent
capability request (`11` in the brainstorm) rather than retrying blindly.

### On REQUIRE_APPROVAL

The request parks in a durable queue and the operator is notified per the intervention model. The
request is **not** re-evaluated by the model in the meantime, and no fallback path may
achieve the same effect through a different capability. Approval decisions carry
`confirm_once` or `always` semantics, borrowed from Argus.

Silence never becomes ALLOW. A request unanswered past its window becomes DENY.

## Executor

The only component holding credentials. Given a `decision_id` and a scope, it:

1. Re-validates that the decision is present, unexpired, and matches the request hash
2. Assumes the narrowest role that satisfies the scope, via STS with a session policy
3. Writes the pre-execution audit record — **if this fails, it stops** (AR-4)
4. Executes, enforcing `cost_ceiling` and a timeout
5. Measures actual cost
6. Writes the result record
7. Returns `CapabilityResult`

The executor never accepts a capability invocation without a decision id, and never accepts
a decision id it did not receive from the policy engine. It is the only place credentials
exist, and it runs in a process the model cannot reach (AR-12).

## CapabilityResult

```text
outcome           SUCCESS | FAILURE | DENIED | REJECTED | DUPLICATE
                  | TIMEOUT | ABORTED_COST | UNKNOWN
canonical_id      c7f3a1...   broker-derived; joins to CloudTrail
actual_cost       { usd, tokens, duration_ms }
artifacts         references to what was produced; never inline blobs
audit_id          aud_01J8...
error             structured, model-readable on failure
```

`artifacts` holds references rather than contents, so that a large result cannot flood model
context and so that artifacts are independently inspectable.

The outcomes are deliberately not collapsed into `FAILURE`, because they call for different
responses and conflating them destroys the signal:

- `DENIED` — policy said no. Rootstock should reconsider, or file a capability request.
- `REJECTED` — failed schema validation. A malformed request is a *bug*, not a decision.
- `DUPLICATE` — already executed. The prior result is returned; nothing new happened.
- `ABORTED_COST` — hit a ceiling. A policy event worth counting, not a malfunction.
- `UNKNOWN` — **the side effect may or may not have occurred.** Execution began and the
  outcome could not be durably established, typically because AUDIT CLOSE failed after the
  provider call. This is a reconciliation incident, never a failure.

`UNKNOWN` is the one that must not be optimized away. The temptation is to resolve it to
`FAILURE`, which is tidy and wrong: a retry then duplicates a side effect that already
happened. Reporting "I do not know" is the honest and safe answer, and the
`execution_semantics.reconciliation` check exists to turn it into a known one by asking the
provider (AR-4).

## The capability vocabulary

Names are hierarchical and stable: `domain.service.action`. The first segment is the trust
zone or external domain, which makes the blast radius legible at a glance.

### Granted at 0.0

Deliberately tiny. This is the entire initial vocabulary:

```text
memory.read                    read institutional and state memory
memory.write                   append a claim or state record
sandbox.s3.create_bucket       create a bucket in Sandbox, tagged
sandbox.s3.put_object          write an object to a Rootstock-owned bucket
sandbox.s3.list                enumerate own buckets
sandbox.logs.read              read CloudWatch logs in Sandbox
```

Six capabilities, all Sandbox-scoped or memory-scoped, none costing more than cents, none
externally visible, none irreversible in any meaningful sense.

That is enough to prove the loop and nothing more, which is the point of 0.0.

### Added by rung

Each addition is a deliberate act with its own grant record.

| Rung | Capabilities added |
| --- | --- |
| 0.1 research | `web.search`, `web.fetch` |
| 0.2 building | `sandbox.lambda.deploy`, `sandbox.dynamodb.create_table`, `sandbox.iam.create_service_role`, `sandbox.*.delete_own` |
| 0.3 deployment | `sandbox.apigateway.create`, `dns.record.write` (delegated zone only) |
| 0.4 external | `comms.email.send`, `comms.email.receive`, `web.publish` |
| 0.5 spending | `spend.infrastructure`, `spend.services` — both hard-capped |
| 0.6 venture | `venture.create`, `venture.kill`, `commerce.*` |

### Never granted

Enumerated so that absence is deliberate rather than accidental:

```text
management.*                   anything in the Management account (AR-1, AR-2)
org.*                          AWS Organizations administration
iam.policy.write               modifying its own permission boundaries (AR-6)
commerce.payout                moving money out — held by nobody
constitution.write             (AR-6)
capability.grant               granting itself anything
```

## Capability declaration

Each capability is declared in the grant store — read-only to the runtime (AR-6) — with
every field required. An underspecified capability is not grantable.

```text
id                      sandbox.s3.create_bucket
schema_version          1
description             Create an S3 bucket in the Sandbox account
zone                    sandbox
parameter_schema        { suffix:  string, pattern ^[a-z0-9-]{3,40}$
                          purpose: string, required }
scope                   buckets prefixed rootstock-sbx-*; tagged at creation
risk_class              low
cost_model              negligible; storage billed to sandbox budget
credential              SandboxOperatorRole, session-scoped
autonomy_level          L3
requires_approval       false
rate_limit              10/day
audit                   full
owner                   Operations
depends_on              —

execution_semantics
  reversible            true
  provider_idempotency  false
  reconciliation        bucket_exists(rootstock-sbx-<suffix>)
  retry_after_unknown   reconcile_then_retry
```

`parameter_schema` is what makes AR-16 enforceable rather than aspirational. The caller
supplies a bucket *suffix* matching a constrained pattern, not a bucket name — the
`rootstock-sbx-` prefix is applied by the executor and cannot be escaped by the request.

`execution_semantics` answers *"is it safe to try this again?"*, which is a property of the
capability and not of the broker. The broker consults it after an expired claim lease and
after an `UNKNOWN` outcome (AR-15, AR-4); it never guesses. `reconciliation` names a
deterministic check that establishes what actually happened by asking the provider rather
than by inferring from local state.

At 0.0 every capability is reversible and every reconciliation is a trivial existence check,
which is precisely why this is the right moment to build the machinery — it can be exercised
end to end with nothing at stake.

## Capabilities encode intent, not provider APIs

The general form of AR-16, and the rule that keeps it from eroding.

The failure is never a single bad decision. Nobody proposes `aws.call()`. What happens is
that a capability grows one more parameter, eight times, until it has reconstructed the
provider API underneath it — and each individual addition looked reasonable.

| Instead of | Declare |
| --- | --- |
| `delete_object(bucket, key)` | `delete_owned_artifact(artifact_id)` |
| `send_http_request(url, method, body)` | `heartbeat.ping()` |
| `assume_role(role_arn)` | `sandbox.s3.create_bucket(suffix)` |
| `run_query(sql)` | `metrics.venture_revenue(venture_id, period)` |
| `put_dns_record(zone, name, type, value)` | `dns.point_subdomain(subdomain, target_venture)` |

The test to apply when declaring or extending a capability:

> **Can the caller express something the capability's name does not promise?**

If yes, the parameter surface is too wide. A caller of `heartbeat.ping()` cannot reach an
arbitrary host; a caller of `send_http_request` can, and no amount of policy on top recovers
the difference — the policy engine would have to understand URLs, which is exactly the
open-ended reasoning that deterministic gates are supposed to avoid.

The corollary is that capability design is where most of the safety work actually happens.
A well-named capability with a narrow schema needs very little policy. A badly-scoped one
cannot be rescued by any amount of it.

## Failure modes this closes

Tracing back to the register in `docs/brainstorm/14-failure-modes.md`:

| Failure | How this closes it |
| --- | --- |
| Prompt injection achieving action | Model cannot execute; `provenance` restricts untrusted-derived requests |
| Runaway cost | `estimated_cost` pre-check, `cost_ceiling` abort, provider cap beneath (AR-8) |
| Aggregate refund cap missing | Aggregate totals are a first-class policy check, not per-request |
| Privilege escalation | `capability.grant` does not exist; scope intersects only (AR-7) |
| Unauditable action | No execution path without an `audit_id` (AR-4) |
| Orphaned resources | Tagging enforced at creation inside the executor (AR-13) |
| Credential leak via model | Credentials never enter model context (AR-12) |
| Duplicated charge, refund, or message | Derived canonical id; claim-before-execute (AR-15) |
| Broker degrades into an AWS shell | Declared ids and parameter schemas only; no generic dispatch (AR-16) |

## Open items

- **Grant store format.** Likely versioned declarative files in a bucket the runtime can
  read and not write, mirroring Argus's `argus.policy.yaml` shape.
- **Capability schema evolution.** `schema_version` exists, but the rules for changing a
  schema without invalidating historical audit records are unwritten. Probably: schemas are
  append-only and a new version is a new declaration.
- **Composite capabilities.** "Deploy an application" is really a sequence. Whether that is
  a capability or an orchestration of capabilities is unresolved; leaning orchestration, so
  each primitive stays independently auditable.
- **Cost estimation quality.** Early estimates will be poor. The estimate-to-actual ratio
  should be tracked from 0.0 so the calibration data exists before it matters.
- **Dry-run mode.** A request evaluated but not executed, for testing policy without side
  effects. Cheap and probably worth having from the start.
