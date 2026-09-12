# Phase 1 — Substrate

> **Verdict: complete.** All five exit criteria passed. Core and Sandbox substrate exist.
> IAM negatives were asserted by `iam:SimulatePrincipalPolicy`, not by reading Terraform.
> Object lock denied a versioned delete of an audit object. Ready for Phase 2.

## Commit / revision

```text
branch          main
base commit     adb37a3  ("Record Phase 0: harness, SSO guards, and first Sandbox cycle.")
working tree    uncommitted — F-1 design + Phase 1 terraform/code/evidence
terraform       infra/v0, local state (not committed)
```

## Environment

```text
Python          3.12.3
uv              0.11.6
Terraform       1.9.8
AWS provider    5.100.0
AWS CLI         2.33.12
OS              Linux 7.0-30-generic
SSO login       2026-08-26T13:43:39Z  (rootstock-core)
                2026-08-26T13:45:31Z  (rootstock-sandbox; separate sso-session)
plan            2026-08-26T13:46Z     36 to add, 0 to change, 0 to destroy
apply started   2026-08-26T13:47:00Z
apply ended     2026-08-26T13:47:55Z
elapsed         56s
```

`make v0-init` had already succeeded before SSO expired. Plan and apply were re-run after
refreshing both SSO sessions. Apply used `-auto-approve` after inspecting the plan.

## Tests run

```text
ruff check src tests scripts        pass (after wrapping one long ARN line)
mypy --strict                       pass
pytest                              73 passed
terraform fmt / validate            pass (test-env and infra/v0)
make aws-context-core               pass
make aws-context                    pass
make v0-init                        pass (earlier this session)
make v0-plan                        pass
terraform apply -auto-approve       36 added, 0 changed, 0 destroyed
make v0-assert-iam                  pass
```

## Destructive tests run

**None.** D1–D8 remain unimplemented. Not required for Phase 1.

## AWS context resolved

```text
profile     rootstock-core
zone        core
account     111111111111
principal   arn:aws:sts::111111111111:assumed-role/AWSReservedSSO_RootstockAdministrator_<id>/operator

profile     rootstock-sandbox
zone        sandbox
account     022222222222
principal   arn:aws:sts::022222222222:assumed-role/AWSReservedSSO_RootstockAdministrator_<id>/operator
```

An unrelated personal `default` profile was never used. Ambient static keys were stripped
by the Makefile. `data.aws_organizations_organization.this` from Core returned the
organization id (not recorded here).

## F-1 resolution (encoded before apply)

Claims are execution-only (`PENDING | EXECUTED | FAILED | UNKNOWN`). `REQUIRE_APPROVAL`
goes to DynamoDB `rootstock-approvals` (`AWAITING_APPROVAL | APPROVED | REJECTED | EXPIRED`)
with no lease. Policy runs before any claim. VERIFY's parked path is an approval-store
lookup.

## Resources created

Core (`111111111111`):

```text
tables      rootstock-memory
            rootstock-decisions
            rootstock-claims
            rootstock-approvals
buckets     rootstock-grant-111111111111
            rootstock-audit-111111111111   object lock GOVERNANCE 30d
queues      rootstock-capability-requests
            rootstock-capability-requests-dlq
roles       rootstock-runtime-role
            rootstock-broker-role
secret      rootstock/model-api-key        placeholder
wake        rootstock-runtime-wake         DISABLED
grant keys  constitution.json
            constitution.sha256            929842efcf61757a70ea38d7a04075dd24dc6524f6b5c1a854ff974a969188bf
            policy.json
            capabilities/memory.read.json
            capabilities/memory.write.json
            capabilities/sandbox.logs.read.json
            capabilities/sandbox.s3.create_bucket.json
            capabilities/sandbox.s3.list.json
            capabilities/sandbox.s3.put_object.json
```

Sandbox (`022222222222`):

```text
role        RootstockSandboxOperatorRole
trust       Core broker role + sts:ExternalId + aws:PrincipalOrgID
```

Independent inventory used `dynamodb:ListTables`, `s3:ListBuckets`, `iam:GetRole`,
`events:DescribeRule`, `s3:ListObjectsV2`, and `sqs:GetQueueUrl` — not Terraform state.

## Exit criteria

### 1–4. IAM negative assertions (`make v0-assert-iam`)

`iam:SimulatePrincipalPolicy` against the live role ARNs from `terraform output`:

```text
OK   runtime has no AssumeRole: sts:AssumeRole → implicitDeny
OK   runtime cannot assume sandbox operator: sts:AssumeRole → implicitDeny
OK   runtime cannot write grant store: s3:PutObject → implicitDeny
OK   runtime cannot delete audit: s3:DeleteObject → implicitDeny
OK   broker cannot delete audit: s3:DeleteObject → implicitDeny
OK   broker cannot read model secret: secretsmanager:GetSecretValue → implicitDeny
OK   broker cannot assume into Management: sts:AssumeRole → implicitDeny
All IAM negative assertions passed.
```

Management target was a placeholder ARN (`arn:aws:iam::000000000000:role/anything`).
Neither role has any `sts:AssumeRole` except the broker's allow on
`RootstockSandboxOperatorRole`, so a Management ARN is implicit deny.

### 5. Object lock — versioned delete denied

Probe object `s3://rootstock-audit-111111111111/phase-1/object-lock-probe.txt`
version `00pLT9kKynze1aN7SsAueCC3c0rsEw9n`:

```text
ObjectLockMode            GOVERNANCE
ObjectLockRetainUntilDate 2026-09-25T13:51:14.307000+00:00
```

A current-key `DeleteObject` (no `VersionId`) succeeded by writing a delete marker. That is
versioning, not lock bypass — the locked version remained readable.

`DeleteObject` **with** that `VersionId` and **without** `x-amz-bypass-governance-retention`:

```text
Access Denied because object protected by object lock.   exit 254
```

`HeadObject` of the same version still succeeds after the denied delete.

## Cost

Apply created empty PAY_PER_REQUEST tables, two empty-ish buckets, two idle queues, two
IAM roles, a disabled EventBridge rule, and a handful of grant-store objects. No Lambda,
no model calls. Cost of this phase is effectively $0.

The probe object remains in the audit bucket under a delete marker until 2026-09-25 unless
explicitly bypassed. Leave it; it is evidence.

## Blocker encountered

SSO tokens had expired (`TokenRetrievalError`). `aws sso login --profile rootstock-core`
and `--profile rootstock-sandbox` were required because the two profiles use **separate**
`sso-session` names (`rootstock` vs `rootstock-sandbox`) against the same start URL. One
login does not cover both.

## Surprise behavior

Object lock does not reject a current-key delete. S3 writes a delete marker and hides the
object at the key. The WORM guarantee is on the **version**. Phase 2 audit writes must
record `VersionId`; CLOSE/VERIFY must read by version, not by key, or a delete marker would
make an OPEN object look missing.

## Ready for Phase 2

Yes. F-1 no longer blocks the claim state machine. Do not start Phase 3 until Phase 2 exit
criteria 2 (replay) and 6 (AUDIT CLOSE failure → UNKNOWN) both pass.
