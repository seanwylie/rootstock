# AWS Setup — Operational Record

> **Status: As built.** This document records what exists, how it is configured, and what
> has been verified. It is a record, not a design.
>
> The *reasoning* behind this structure lives in `docs/design/00-system-boundaries.md`. The
> architectural requirements it satisfies are the `AR-*` identifiers cited throughout.
> Where this document and the design documents disagree, one of them is wrong and it should
> be fixed rather than reconciled in the reader's head.

## Summary

A dedicated AWS Organization exists for Rootstock with three accounts: a Management account
that controls everything and runs nothing, and two member accounts — Core and Sandbox.
Human access to the member accounts is through IAM Identity Center.

**Lambdas exist in Core. Wake is DISABLED, still on the stub.**
`rootstock-runtime` proposes via SQS; `rootstock-broker` executes under a session policy.
Only `lambda.amazonaws.com` can assume either role. Qualification:
`docs/plans/v0/evidence/phase-7.md`. Destructive controls:
`docs/plans/v0/evidence/phase-5.md`. Model adapter (live still stub):
`docs/plans/v0/evidence/phase-6.md`.

---

## Legal ownership

```text
Sean Wylie, doing business as Wise Kids Studios
```

Rootstock is a software project, not a legal person. Wise Kids Studios is a trade name.
AWS accounts, domains, payment accounts, IP, and cloud resources remain legally controlled
by the human owner regardless of how much operational authority is later delegated.

---

## Organization structure

```text
Wise Kids Studios
        │
        ▼
┌───────────────────────────────┐
│ Rootstock  (Management)       │  AWS Organizations
│                               │  Consolidated billing
│  NO WORKLOADS  (AR-1)         │  Centralized member-account root
│  NO ROOTSTOCK CREDENTIALS     │  IAM Identity Center
└───────────────┬───────────────┘  Break-glass
                │
        ┌───────┴────────┐
        ▼                ▼
┌───────────────┐ ┌───────────────┐
│ Rootstock     │ │ Rootstock     │
│ Core          │ │ Sandbox       │
│               │ │               │
│ runtime+broker│ │ operator role │
│ Lambdas       │ │ (via broker)  │
│ wake DISABLED │ │               │
└───────────────┘ └───────────────┘
```

The organization was created from a fresh AWS account rather than an existing Wise Kids
Studios workload account, so that Management remains a dedicated control-plane account.

Both member accounts hold Phase 1 substrate. Phase 3 deploys the runtime and broker
Lambdas in Core. The wake rule is `DISABLED` after stub qualification. Live `REASONER`
remains `stub` until Phase 7b.

### Account identities

These are the only AWS accounts this repository is allowed to target. Encoded in the
operator-local `infra/accounts.json` (copy `infra/accounts.example.json`) and enforced by
`scripts/check_aws_context.py` plus Terraform `allowed_account_ids`. An unrelated `default`
profile is forbidden by name.

| Zone | Account name | Account ID | SSO profile | Role |
| --- | --- | --- | --- | --- |
| Management | Rootstock | *not encoded in this repo* | none | Organizations / break-glass |
| Core | Rootstock Core | local `accounts.json` | `rootstock-core` | RootstockAdministrator |
| Sandbox | Rootstock Sandbox | local `accounts.json` | `rootstock-sandbox` | RootstockAdministrator |

Management has no profile here on purpose. There is no name a command can pass that resolves
to it, so tooling cannot target it even by mistake (AR-1, AR-2).

Rootstock commands never use `default`. They require `rootstock-core` or
`rootstock-sandbox` explicitly. `make infra-*` targets Sandbox and will refuse to run unless
`aws sts get-caller-identity --profile rootstock-sandbox` returns the Sandbox account id
from `infra/accounts.json` via an assumed Identity Center role.

### Account roles

| Account | Purpose | Rootstock workloads |
| --- | --- | --- |
| **Rootstock** (Management) | Organizations, billing, Identity Center, centralized root, break-glass | Never (AR-1) |
| **Rootstock Core** | Runtime, memory, ledger, policy engine, audit | runtime + broker Lambdas; wake DISABLED (stub) |
| **Rootstock Sandbox** | Experiments, prototypes, disposable infrastructure | Operator role, assumed per invocation |

Venture accounts do not exist and are not needed until rung 0.6.

### Permitted authority directions

```text
Management → Core / Sandbox        allowed
Core       → Sandbox               allowed; broker role may assume operator role
Anything   → Management            prohibited  (AR-2)
```

---

## Management account

Account name: `Rootstock`. Role: AWS Organizations management account.

**Enabled:**

- AWS Organizations, with account creation and consolidated billing
- Centralized root access for member accounts, comprising root credentials management and
  privileged root actions
- IAM Identity Center (organization instance)

**No delegated administrator is configured.** Management therefore remains the sole
authority for member-account root operations.

**Member-account root credentials:** persistent root credentials are not created for member
accounts. Where root-level action is required, centralized privileged root access is used
instead. This prevents member accounts from holding independent root identities that could
escape organization-level control.

---

## IAM Identity Center

```text
Instance type     Organization instance
Primary region    us-east-1 (US East, N. Virginia)
Deployment        Single Region
Identity source   IAM Identity Center directory (built-in)
```

Multi-Region was intentionally not enabled — unnecessary complexity at current scale.

### Human identity

```text
User              operator
Permission set    RootstockAdministrator  (AdministratorAccess)
Assigned to       Rootstock Core, Rootstock Sandbox
NOT assigned to   Rootstock (Management)
```

```text
              operator
                │
       IAM Identity Center
                │
      RootstockAdministrator
         /              \
        ▼                ▼
      Core            Sandbox

      Management
          ▲
          │  no normal SSO assignment
```

Management is reached separately, as the constitutional layer. `AdministratorAccess` is
appropriate during infrastructure construction; narrower sets (`RootstockDeveloper`,
`RootstockReadOnly`, `RootstockSecurityAudit`, `RootstockBillingReadOnly`) may follow.

**Human administrator access and Rootstock machine access remain separate concepts and must
not be merged.**

### MFA

Management and root access require MFA. The human Identity Center administrator requires
MFA. Machine identities use workload identities and STS temporary credentials, never MFA or
interactive credentials.

---

## Verified

Tested and confirmed working:

```text
[x] Identity Center sign-in through the AWS access portal
[x] Assumption of RootstockAdministrator into Rootstock Sandbox
[x] Assumption of RootstockAdministrator into Rootstock Core
[x] S3 console access within Sandbox
[x] Management does not appear as a normal assigned SSO target
[x] CLI profiles `rootstock-sandbox` and `rootstock-core` resolve to the mapped accounts
[x] CLI `default` profile is forbidden by name and is not a Rootstock account
```

---

## Completed checklist

```text
[x] Dedicated Rootstock AWS management account
[x] Dedicated AWS Organization, created from a fresh account
[x] Management kept separate from existing Wise Kids Studios workloads
[x] Centralized root access enabled
[x] Root credentials management enabled
[x] Privileged member-account root actions enabled
[x] No delegated centralized-root administrator
[x] Rootstock Core member account created
[x] Rootstock Sandbox member account created
[x] IAM Identity Center enabled as an organization instance, us-east-1, single Region
[x] Built-in Identity Center directory in use
[x] Human Identity Center administrator created and assigned to Core and Sandbox
[x] Human administrator NOT assigned via SSO to Management
[x] RootstockAdministrator permission set established
[x] Access path tested against Sandbox
[x] Phase 1 Core substrate (tables, grant/audit buckets, SQS, IAM roles)
[x] Phase 1 Sandbox operator role with ExternalId + PrincipalOrgID + tagged create
[x] IAM negative assertions on runtime and broker roles
```

---

## Deliberately not implemented

Items still unchecked do not exist. Checked items exist but are called out so the
remaining 0.0 gap (live model inference) stays visible.

```text
[x] Lambda functions assuming the Phase 1 roles
[x] EventBridge wake enabled
[x] Unattended process holding a Rootstock role
[ ] Service Control Policies (halt SCP `rootstock-budget-halt` exists in Management, unattached)
[ ] System / Sandbox / Ventures OUs
[ ] Quarantine OU
[ ] Dedicated Security account
[ ] Central logging account
[ ] Organization CloudTrail architecture
[ ] GuardDuty / Security Hub / AWS Config organization configuration
[x] Budget enforcement actions (Core + Sandbox member budgets; org backstop `rootstock-org-monthly`)
[ ] Automated cost anomaly response
[ ] Resource-tagging enforcement
[ ] Region restrictions
[ ] Venture-account provisioning
```

Lambdas exist and the wake rule is `DISABLED` after stub qualification. Live
`REASONER=model` is Phase 7b, not 0.1. Member-account AWS Budgets with automatic IAM-attach actions exist
in Core and Sandbox (`infra/v0/budgets.tf`). Organization CloudTrail is still unbuilt;
Phase 5/7 joined Sandbox `CreateBucket` events via Event history.

---

## Next AWS work

Ordered, and scoped to what rung 0.0 actually requires
(`docs/design/01-rootstock-v0.md`).

Phase 1 closed the substrate items below (1–3, 5, 7). Phases 3–7 attached compute, proved
liveness, ran `D1`–`D8`, inserted `ModelReasoner` without flipping the live Lambda, and
qualified 100 unattended stub cycles (Phase 7a). Member-account AWS Budgets and the
Management org backstop exist. Remaining AWS work is a deliberate Phase 7b Terra run —
not 0.1.

### 1. Runtime identity in Core — **done (Phase 1)**
Two IAM roles, matching the process split in the v0 design. Full policies in
`docs/design/03-runtime-and-broker.md`. No Lambda is attached yet.

```text
rootstock-runtime-role    Bedrock Terra only; read own state; append memory + decisions;
                          sqs:SendMessage
                          NO sts:AssumeRole, anywhere

rootstock-broker-role     sqs:ReceiveMessage; audit PutObject (no Delete);
                          sts:AssumeRole into Sandbox only
                          NO model access
```

The runtime necessarily has AWS credentials — every Lambda does. What it must not have is
**side-effect authority**: the total absence of `sts:AssumeRole` from its policy is the
bright line, and it is trivially auditable.

The separation is what makes AR-3 and AR-12 real rather than nominal.

### 2. Request queue and claim table in Core — **done (Phase 1)**
An SQS queue carries `CapabilityRequest` from runtime to broker, with a dead-letter queue
alarmed to the operator. A DynamoDB claim table gives the broker replay safety (AR-15) — one
authorized request produces at most one side effect.

A standard queue is used deliberately: at-least-once delivery means idempotency is exercised
in normal operation rather than only during incidents.

### 3. Sandbox operator role — **done (Phase 1; tagging conditions corrected in Phase 2)**
`RootstockSandboxOperatorRole` in Sandbox, trusting only `rootstock-broker-role` from Core,
gated on `ExternalId` and `aws:PrincipalOrgID`. Permissions limited to the capabilities
granted at 0.0 — bucket create, tagging, put/list within a `rootstock-sbx-*` prefix, and
CloudWatch Logs read. `aws:RequestTag` conditions were removed in Phase 2: S3 does not
populate them on `CreateBucket` or `PutBucketTagging`, so they denied every live call.
Tags are applied by the broker executor and verified by reading the bucket.

Two independent controls, both explicit: *can the role be assumed*, and *what can it do once
assumed*. A per-invocation session policy narrows further, so effective permissions are an
intersection and widening is impossible (AR-7).

### 4. Provider-enforced budget caps (AR-8) — **AWS member caps in place; Bedrock is AWS spend**
AWS Budgets with enforcement actions, not alerts. Sized as a percentage of treasury rather
than a fixed dollar figure. Must sever service rather than notify.

The payer enabled member-account budgets. Terraform (`infra/v0/budgets.tf`) manages:

| Account | Budget | Limit | Automatic action |
| --- | --- | --- | --- |
| Core | `rootstock-core-monthly` | $10 / month | Attach `rootstock-budget-sever` (Deny `*`) to `rootstock-runtime-role` and `rootstock-broker-role` |
| Sandbox | `rootstock-sandbox-monthly` | $10 / month | Attach `rootstock-budget-sever` to `RootstockSandboxOperatorRole` only |

Execution role in each account: `rootstock-budgets-actions` (trusted by `budgets.amazonaws.com`).
Notifications go to the address in `terraform.tfvars` (`budget_alert_email`).

Inference is Amazon Bedrock (GPT-5.6 Terra geo CRIS `us.openai.gpt-5.6-terra`) via
`bedrock:InvokeModel` on `rootstock-runtime-role`. There is no `rootstock/model-api-key`.
Bedrock usage bills in Core and is therefore inside `rootstock-core-monthly`. Do not
generate a Bedrock API key; do not grant `bedrock:CallWithBearerToken`.

The broker has no Bedrock permission. The runtime cannot assume Sandbox roles. IAM pins
Terra; the prompt cannot escalate to another model.

OpenAI models on Bedrock have no console “enable” button and are not AWS Marketplace
products. Listing as `ACTIVE` is not entitlement to invoke. On 2026-08-28, Core
in **us-east-1** listed `us.openai.gpt-5.6-terra` as an ACTIVE geo
CRIS profile, then `bedrock-runtime Converse` returned `AccessDeniedException`:
`openai.gpt-5.6-terra is not available for this account` (contact AWS Sales). The
Bedrock playground “code example” uses the mantle id `openai.gpt-5.6-terra` and
fails the same way. Rootstock does **not** use `bedrock-mantle`, API keys, or
`CallWithBearerToken`. IAM already pins Terra. Do this in **Core**, region
**us-east-1**. Do not use Management or Sandbox. Do not set `REASONER=model` until
a single supervised `Converse` to `us.openai.gpt-5.6-terra` succeeds. Adapter
`SpendCap` (`max_usd_per_call` in `prompts/v0.json`) is additional, not primary.

Management (hand-operated, not in this repo): SCP `rootstock-budget-halt` (Deny `*`),
role `rootstock-budgets-actions`, and org budget `rootstock-org-monthly` ($25, linked-account
filter Core + Sandbox). The budget action attaches that SCP
to those two accounts automatically at 100% actual. The SCP still has zero targets; do not
attach it by hand. Recovery is detach from Management (SCPs do not apply there). The
Budgets console cannot target member accounts for an SCP action (OU picker only); the
action was created with `budgets create-budget-action` from Management CloudShell.

Prompt `prompts/v0.json` is in the grant store. Runtime env `REASONER=stub`.
See `docs/plans/v0/evidence/phase-6.md`.

### 5. Audit storage the runtime cannot erase (AR-4) — **done (Phase 1)**
An S3 bucket in Core where `rootstock-broker-role` holds `PutObject` and not `DeleteObject`,
with object lock. `rootstock-runtime-role` holds neither. Phase 5 joined Sandbox mutations
to claims via CloudTrail Event history (`canonical_id` as session name). An organization
trail can follow later.

### 6. Heartbeat and liveness monitoring (AR-10) — **done (Phase 4)**
`heartbeat.ping()` GETs a fixed HTTPS URL at the end of every cycle. The URL is Lambda
configuration, not an argument. The sink is a Function URL in Core that the runtime cannot
write to except by HTTP; a separate watch Lambda alarms on silence. DLQ and expired-lease
CloudWatch alarms exist. The runtime cannot disable the watch, delete the alarms, fake
`last_ping`, or change `HEARTBEAT_URL` (IAM simulate). Wake is `DISABLED` after stub
qualification; the silence window is 7 days so the watch does not sit in ALARM. See
`docs/plans/v0/evidence/phase-4.md` and `docs/plans/v0/evidence/phase-7.md`.

### 7. Tagging at creation (AR-13) — **executor + verification (Phase 2 finding)**
S3 does not surface `aws:RequestTag` on `CreateBucket` or `PutBucketTagging`, so IAM cannot
refuse an untagged bucket. The executor writes the required tags immediately after create.
A reconciliation sweep is still required for the window between those two calls. See
`docs/design/03-runtime-and-broker.md` and `docs/plans/v0/evidence/phase-2.md`.

### 8. SCP baseline
Deferred until ventures exist, with one exception: a policy denying member accounts the
ability to leave the organization is cheap and worth having now.

---

## Future shape

For orientation only. None of this is committed.

```text
Wise Kids Studios
        │
        ▼
  Rootstock Management
        │
   ┌────┼─────┬──────────┐
   ▼    ▼     ▼          ▼
Security Core Sandbox  Ventures OU
                        ├── Venture A
                        ├── Venture B
                        └── ...
```

A venture earns a dedicated account when its profile justifies isolation: customer data,
payment processing, meaningful revenue, an independent deployment lifecycle, public exposure,
separate secrets, or the possibility of being sold. Accounts are security boundaries, not
organizational labels.

A `Quarantine` OU is desirable eventually — for compromised, abandoned, unexpectedly
expensive, or under-investigation accounts. It would restrict resource creation, egress, IAM
mutation, and role assumption while preserving logs, evidence, and billing history. Deleting
an account should not be the first incident-response action.

---

## Cost attribution

Not yet enforced. When resources exist, every one should carry:

```text
rootstock:owner
rootstock:venture
rootstock:environment
rootstock:purpose
rootstock:cost-center
rootstock:managed-by
```

Attribution feeds venture-level economics (`docs/brainstorm/03-economic-model.md`). Financial
figures come from AWS billing, Cost Explorer, CUR exports, and the ledger — never from model
memory (AR-5).
