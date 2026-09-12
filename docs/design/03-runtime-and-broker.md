# 03 — Runtime and Broker

> **Status: Decided.** This document is normative. It specifies the protocol between
> `rootstock-runtime` and `rootstock-broker`, the identity graph that enforces the split,
> and the replay-safety mechanics required by AR-15.

## Why this document exists

The process split in `01-rootstock-v0.md` is only as strong as the interface between the two
halves. Two ways to have the split on paper and not in practice:

- **A generic proxy.** If the broker accepts `aws.call(service, operation, params)`, the
  runtime has an AWS shell and the split bought nothing. Prevented by AR-16.
- **An over-permissioned runtime.** If the runtime holds `sts:AssumeRole` into Sandbox
  "just for reads," the broker is optional rather than mandatory.

This document specifies the interface narrowly enough that neither is possible.

## Credential precision

The phrase *"the runtime holds no AWS credentials"* is wrong and should not be used. A
Lambda necessarily executes with an execution role and therefore always has temporary AWS
credentials. Writing a requirement that AWS makes impossible to satisfy guarantees it will
be quietly violated.

The accurate statement:

> **`rootstock-runtime` has no AWS side-effect authority.** It can read its deterministic
> observation state, append to the memory and decision stores, and enqueue a
> `CapabilityRequest`. It holds no `sts:AssumeRole` permission of any kind, no authority in
> Sandbox, and no permission to mutate the grant store or the audit store.

The distinction that matters is not *credentials vs. no credentials*. It is **authority over
Rootstock's own bookkeeping** versus **authority to act on the world.** The runtime has the
first. Only the broker has the second.

Appending a decision record is a side effect in the strict sense, and it is deliberately
allowed: a runtime that cannot record its own reasoning cannot be audited. What it cannot do
is *change* anything already recorded, or reach anything outside Core.

## The protocol

The runtime does not call the broker. It emits an immutable request into a deterministic
boundary and exits.

```text
rootstock-runtime
        │
        │  CapabilityRequest  (immutable, schema-versioned)
        ▼
   SQS  rootstock-capability-requests
        │
        ▼
rootstock-broker
        │
        ├── 1. schema validation          AR-16   reject unroutable
        ├── 2. policy evaluation          AR-3    ALLOW/DENY/REQUIRE_APPROVAL
        ├── 3. claim (ALLOW only)         AR-15   reject duplicate execution
        ├── 4. audit precondition         AR-4    fail closed
        ├── 5. execute                    ≤ 1 capability, scoped session
        └── 6. record + close             actual cost, outcome, audit id
```

Ordering is deliberate. Schema validation precedes everything because an unroutable request
should never reach policy code. Policy precedes claiming because a lease means work is
in flight — `REQUIRE_APPROVAL` is not work, and must not occupy `PENDING` (F-1). Replay of
an allowed request is still caught by the claim table; replay of a parked request is caught
by the approval store.

### Why asynchronous

**Decision: SQS between runtime and broker, not direct invocation.** `[DECIDED]`

Synchronous invoke would be simpler, but it forces the runtime to block on the broker, which
contradicts the dormancy property that makes the v0 loop cheap and restartable. It also puts
`lambda:InvokeFunction` in the runtime's role, which is a smaller version of the authority we
are trying to withhold.

Asynchronous has a more useful consequence: **the previous cycle's result becomes part of the
next cycle's observation.** That is exactly what `expected_outcome` was designed for, and it
makes the `prior cycle closed` check in VERIFY load-bearing rather than decorative. The
organism predicts, sleeps, and then confronts what actually happened.

**A standard queue, not FIFO.** At-least-once delivery is a feature here: it makes AR-15
unavoidable rather than theoretical, and it is exercised in normal operation rather than
only during incidents. Correctness must not depend on transport guarantees, because
transports get replaced. FIFO with content-based deduplication may be added later as
defense in depth, but the broker must remain correct without it.

## Request identity

The runtime supplies an **idempotency key**. The broker derives the **canonical request id**.
The runtime never chooses the id under which its request is deduplicated.

```text
runtime supplies:
    idempotency_key = cycle_number
    capability, target, parameters, estimated_cost, justification, provenance

broker derives:
    canonical_id = sha256(
        idempotency_key ‖ capability ‖ target ‖ canonical_json(parameters)
    )
```

This ordering matters. If the runtime supplied an opaque request id, it could evade
deduplication by varying it — accidentally through a retry bug, or deliberately. Deriving
the id from the request *content* means two logically identical requests collide by
construction, and a request whose parameters differ is correctly treated as new.

### The two halves do different jobs

**Identical request** and **same intended operation** are not synonyms, and the scheme must
not conflate them:

> **The idempotency key identifies the logical operation instance. The content hash prevents
> mutation and retry games within that instance.**

At 0.0 the distinction is invisible, because one cycle permits one action and the
capabilities are trivial. It becomes load-bearing later. `send_email(to=X, body=Y)` sent
deliberately on Monday and again deliberately on Tuesday is byte-identical and is two
legitimate operations; the cycle-derived key separates them correctly, while pure content
addressing would silently swallow the second as a duplicate.

**Do not drift toward pure content-addressing.** It is tempting, because dropping the key
makes deduplication look more principled, and it would introduce a class of bug where
Rootstock cannot repeat a legitimate action — failing silently, with a `DUPLICATE` that
looks like success.

The general rule for choosing an idempotency key: it must be stable across *retries of one
intent* and distinct across *separate intents*. Cycle number satisfies this at 0.0. When
multiple actions per cycle arrive at 0.2, it becomes cycle plus an intra-cycle sequence.

## Claiming and execution

The hard part of idempotency is not detecting duplicates. It is the crash between claiming a
request and completing it — naive deduplication turns that into a side effect that never
happens and can never be retried.

**F-1 `[SETTLED]`: the claim table is for execution, not for parking.** A lease models "a
process is working on this." Nothing is working on a request waiting for the operator, so that
request must not sit as `PENDING`. Mixing the two made waiting for approval look identical
to a broker that died mid-flight — VERIFY would halt, the operator would learn to ignore the
alert, and AR-10 would be defeated through a different door.

### Claim table — in-flight and terminal execution only

Keyed by canonical id:

```text
canonical_id      PK
state             PENDING | EXECUTED | FAILED | UNKNOWN
lease_expires_at  epoch seconds     # meaningful only in PENDING
attempt           integer
result_ref        pointer to CapabilityResult, once terminal
```

`PENDING` means the broker currently holds a lease and is executing, or crashed while doing
so. It is never a waiting room.

The broker claims with a conditional write, **and only after policy has returned ALLOW**:

```text
attribute_not_exists(canonical_id)
  OR (state = PENDING AND lease_expires_at < now)
```

Three outcomes:

- **Claim succeeds, no prior record** — first attempt. Execute.
- **Claim succeeds, prior PENDING record expired** — the previous attempt died mid-flight.
  Take over and increment `attempt`. What happens next is decided by the capability's
  declared `execution_semantics.retry_after_unknown`, never by broker judgment. For every
  0.0 capability this is `reconcile_then_retry`: run the declared reconciliation check, and
  retry only if it confirms the side effect did not occur. A capability declaring neither
  reversibility nor a reconciliation strategy halts and escalates.
- **Claim fails** — the request is in flight or already terminal. Return the stored result
  with outcome `DUPLICATE`. No execution, no budget consumed.

`UNKNOWN` is deliberately **not** terminal. It marks a claim whose real-world effect was
never established, and it holds the request out of both the success and failure paths until
reconciliation resolves it.

The lease must comfortably exceed the executor timeout, so an expired lease genuinely means
the attempt is dead rather than slow.

### Approval store — parked, lease-exempt

Separate table, also keyed by canonical id:

```text
canonical_id      PK
state             AWAITING_APPROVAL | APPROVED | REJECTED | EXPIRED
requested_at
expires_at        the unanswered window, after which silence is DENY (`15`)
decision_ref
request           the CapabilityRequest, immutable
```

When policy returns `REQUIRE_APPROVAL`, the broker writes this record and **does not
claim**. There is no lease because there is no in-flight work. VERIFY's "open, awaiting
approval" path is a lookup here, not an expired `PENDING` claim.

Replay of an identical request finds the approval row and returns the parked state rather
than opening a second one.

Silence past `expires_at` becomes `REJECTED` / DENY. It never becomes ALLOW, and it never
becomes an expired-lease halt.

Approval transport (how the operator is notified) remains deferred to 0.4. The store itself is
required now so Phase 2 cannot encode the wrong state machine.

### Pipeline order

```text
schema validation
        │
        ▼
policy evaluation          ALLOW | DENY | REQUIRE_APPROVAL
        │
        ├── DENY               record, close decision, no claim
        ├── REQUIRE_APPROVAL   write approval store, leave decision open, no claim
        └── ALLOW
                │
                ▼
              claim            AR-15
                │
                ▼
           audit open          AR-4
                │
                ▼
             execute
```

Claiming before policy was the bug: it forced every outcome, including "please wait," into
a leased `PENDING` row. Policy first means the claim table only ever sees work that is
allowed to happen.

## Two-phase audit

AR-4 requires the audit record to precede the action, but the outcome does not exist until
afterward. Audit is therefore split, and the split has a sharp asymmetry.

```text
AUDIT OPEN     canonical_id, capability, parameters,
               policy decision, intended action, timestamp
     │
     │  durable write MUST succeed
     │  ── fails ──▶ no execution. Fail closed. This is D7.
     ▼
EXECUTE        assume scoped session, one provider call
     │
     ▼
AUDIT CLOSE    actual outcome, provider identifiers, cost, error, timestamp
     │
     └── fails ──▶ outcome UNKNOWN, claim state UNKNOWN, incident raised
                   NOT FAILURE
```

**Fail-closed applies only to AUDIT OPEN.** After the provider call has happened, failing
closed is no longer an option — the thing occurred. The only remaining choice is what to
record about it, and recording `FAILURE` would be a confident lie that invites a retry and
duplicates a real side effect.

This is the sequencing bug the design exists to prevent:

```text
WRONG                          RIGHT
execute()                      audit_open()      durable
audit()                        execute()
                               audit_close()     best effort, UNKNOWN on failure
```

The wrong version passes every happy-path test and cannot satisfy AR-4 under any failure at
all. It is worth stating explicitly because the two differ by one line and read almost
identically.

Resolution of `UNKNOWN` is by reconciliation, using the capability's declared strategy: ask
the provider what is true, then close the record with the answer. The provider is the
authority; local state is not. If reconciliation is unavailable or ambiguous, the incident
escalates to the operator rather than being resolved by inference.

## The IAM graph

Precise, because this is the part that either enforces the architecture or doesn't.

### Core — `rootstock-runtime-role`

```text
ALLOW
  logs:CreateLogStream, logs:PutLogEvents      own log group only
  dynamodb:GetItem, Query                      rootstock-memory
  dynamodb:PutItem                             rootstock-memory        (append claims)
  dynamodb:GetItem, Query                      rootstock-decisions
  dynamodb:PutItem                             rootstock-decisions     (open a record)
  dynamodb:GetItem                             rootstock-claims        (VERIFY lease)
  dynamodb:GetItem                             rootstock-approvals     (VERIFY parked)
  s3:GetObject                                 grant store bucket
  sqs:SendMessage                              rootstock-capability-requests
  secretsmanager:GetSecretValue                model API key secret only

DENY / ABSENT
  sts:AssumeRole                               any principal, any account
  s3:PutObject, s3:DeleteObject                audit bucket
  s3:PutObject                                 grant store bucket
  dynamodb:UpdateItem, DeleteItem              all tables
  lambda:InvokeFunction                        all functions
  everything in Sandbox
  everything in Management
```

`sts:AssumeRole` being wholly absent is the single most important line. It is a bright line
and trivially auditable — if the runtime role's policy ever grows an `sts:AssumeRole`, the
architecture has been broken regardless of what else is true.

`PutItem` without `UpdateItem` or `DeleteItem` gives append-only semantics: the runtime can
open a decision record and can never alter one.

### Core — `rootstock-broker-role`

```text
ALLOW
  logs:CreateLogStream, logs:PutLogEvents      own log group only
  sqs:ReceiveMessage, DeleteMessage,           rootstock-capability-requests
      GetQueueAttributes
  dynamodb:PutItem, UpdateItem (conditional)   rootstock-claims
  dynamodb:PutItem, UpdateItem                 rootstock-approvals
  dynamodb:UpdateItem                          rootstock-decisions     (close a record)
  s3:GetObject                                 grant store bucket
  s3:PutObject                                 audit bucket            (NO DeleteObject)
  sts:AssumeRole                               RootstockSandboxOperatorRole ONLY

DENY / ABSENT
  secretsmanager:GetSecretValue                model API key           (AR-12)
  bedrock:*, or any model invocation
  s3:DeleteObject                              audit bucket            (AR-4)
  s3:PutObject                                 grant store bucket      (AR-6)
  any network egress to a model provider
  everything in Management
```

The broker cannot reach a model, by policy and by network configuration. That is the
converse guarantee to the runtime having no `sts:AssumeRole`, and together the two make the
split symmetric: neither half can become the whole.

Trust is `lambda.amazonaws.com` only. The Phase 2 fixture principal was removed when the
broker Lambda became the caller.

### Sandbox — `RootstockSandboxOperatorRole`

Trust policy admits exactly one principal:

```text
Principal   arn:aws:iam::<core>:role/rootstock-broker-role
Condition   sts:ExternalId matches the provisioned value
            aws:PrincipalOrgID matches the Rootstock organization
```

Maximum permissions — the ceiling, not the grant:

```text
s3:CreateBucket        on rootstock-sbx-*
s3:PutBucketTagging    on rootstock-sbx-*
s3:PutObject           on rootstock-sbx-*/*
s3:GetObject           on rootstock-sbx-*/*
s3:ListBucket          on rootstock-sbx-*
logs:FilterLogEvents,  on Sandbox log groups
    GetLogEvents,
    DescribeLogGroups
```

**Phase 2 finding (AR-13).** `aws:RequestTag` on `s3:CreateBucket` and `s3:PutBucketTagging`
does not bind. IAM `SimulatePrincipalPolicy` reports allowed when RequestTag context is
supplied; the live S3 APIs do not populate those keys, so the same conditions implicit-deny
every real call. Tags are applied by the executor immediately after create and verified by
reading the bucket. AR-13 as written in `00` already names tagging policy plus a
reconciliation sweep — that sweep is load-bearing for the create-then-tag window, not
optional cleanup. An untagged `rootstock-sbx-*` bucket can exist if the process dies between
the two calls.

### Scope intersection at assume time

AR-7 requires that delegation narrow rather than widen. The role's policy above is the
*ceiling*. For each individual invocation the broker attaches a **session policy** derived
from the specific capability's declared scope:

```text
AssumeRole(
    RoleArn      = RootstockSandboxOperatorRole
    SessionName  = <canonical_id>
    Policy       = <session policy for this capability only>
    DurationSeconds = 900
)
```

Effective permissions are the intersection of the role policy and the session policy, which
is an AWS guarantee rather than something Rootstock enforces. Widening is therefore
structurally impossible: a session policy cannot grant anything the role lacks.

Using `canonical_id` as the session name is a small but valuable detail — it makes every
CloudTrail event directly joinable to the decision record that caused it, which is what
makes criterion 3 of the v0 success criteria ("decision log and CloudTrail reconcile
exactly") mechanically checkable rather than a manual exercise.

### Management

No role. No trust relationship. No principal in Core or Sandbox may assume into Management,
and nothing in Management references either (AR-1, AR-2).

## Heartbeat

AR-10 requires liveness observed by something that is not Rootstock. A CloudWatch alarm in
Core is insufficient on its own — it shares a blast radius with the thing it monitors.

**Decision: a dead-man's-switch ping to an external monitor**, emitted by the runtime at the
end of each cycle. `[DECIDED]` Configured by the operator, outside AWS, alerting to the operator directly.
Rootstock cannot silence it, extend its window, or delete it, because none of those controls
are inside Rootstock. A CloudWatch alarm on cycle metrics may be added as a secondary
signal.

This is not "external communication" in the sense the README defers to 0.4. The categorical
difference is worth writing down, because the heartbeat is the first outbound packet
Rootstock ever sends and it will be cited as precedent:

| | Heartbeat | External communication (0.4) |
| --- | --- | --- |
| Destination | Fixed, human-configured | Potentially chosen by Rootstock |
| Content | Protocol-defined | Rootstock-authored |
| Recipient | Fixed — the operator | Potentially a customer |
| Rootstock may choose recipient | No | Yes |
| Rootstock may author content | No | Yes |
| Reply channel | None | Yes |
| Purpose | Telemetry | Business operation |

Placing the ping in the runtime rather than the scheduler is deliberate: a wedged cycle, a
crashed function, and a scheduler that never fired then all produce the same observable —
silence.

### Egress constraint

Needing a heartbeat must not hand Rootstock general HTTPS. The capability is
`heartbeat.ping()` and takes no arguments; the URL is configuration the runtime reads and
cannot vary. **There must be no `http_request(url, method, body)` helper in the codebase**,
because the moment one exists, every future need routes through it and AR-16 is defeated by
convenience rather than by attack.

Perfect egress filtering is not required at 0.0 — a VPC endpoint policy or an allowlisted
egress proxy can follow. What is required now is that the *code surface* expose intent
rather than transport, so that tightening the network layer later is a configuration change
rather than a refactor.

## Failure and retry semantics

| Failure | Behavior |
| --- | --- |
| Runtime crashes before enqueue | No request exists. Next wake sees an unclosed decision record and reconciles |
| Runtime crashes after enqueue | Broker proceeds normally. Result lands; next wake reads it |
| Duplicate SQS delivery | Claim fails; `DUPLICATE` returned; no second side effect (AR-15) |
| Broker crashes before claim | Message returns to the queue. Retried cleanly |
| Broker crashes after claim, before AUDIT OPEN | Lease expires; clean takeover, nothing happened |
| AUDIT OPEN fails | No execution. Fail closed (`D7`) |
| Broker crashes after execution, before AUDIT CLOSE | Claim left `UNKNOWN`; reconciliation establishes truth from the provider, never re-executes blindly |
| AUDIT CLOSE fails | Outcome `UNKNOWN`, incident raised. **Never recorded as `FAILURE`** |
| Schema validation fails | Rejected at ingress; recorded; never reaches policy |
| Policy returns DENY | Recorded with the deciding rule; decision record closed as denied |
| Policy returns REQUIRE_APPROVAL | Written to the approval store, **no claim**; decision record stays open; VERIFY sees parked, not an expired lease |
| Message exceeds redrive limit | Dead-letter queue; alarm to the operator; loop halts rather than accumulating failures |

The dead-letter queue matters more than it looks at this scale. Without it, a persistently
malformed request retries forever, quietly burning the inference budget that produced it.

## Open items

- **Approval transport.** The approval *store* exists (F-1). How the operator is notified is
  unspecified until 0.4. Until then, approval means reading the table.
- **Session policy generation.** Whether the session policy is authored per capability in
  the grant store or generated from the declared scope. Leaning authored, since generated
  IAM is difficult to review and review is the point.
- **Claim table TTL.** Terminal claim records should expire eventually, but not before the
  replay window they protect. Interacts with how far back a request could plausibly be
  redelivered.
- **Broker in a separate account.** Stronger than a separate function, and probably
  premature. The interface above does not change if it moves.
