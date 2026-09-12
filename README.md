# Rootstock

Rootstock is an autonomous venture operating system designed to discover, create, operate,
and fund sustainable digital businesses under deterministic economic and governance
constraints.

**Experimental software, released for study and adaptation. Maintained as time permits. No
production-support commitment.**

Created and operated by Sean Wylie, doing business as Wise Kids Studios. Rootstock is a
software project, not a legal person.

Two principles do most of the work:

> **LLMs propose; deterministic systems constrain, execute, measure and account.**
>
> **Autonomy is granted through capabilities, not assumed through intelligence.**

---

## Current phase: architecture / bootstrap

**Implemented**

- Dedicated AWS Organization
- Management / Core / Sandbox isolation
- Human SSO via IAM Identity Center
- Centralized member-account root management
- Phase 0 test harness (Sandbox apply/destroy cycle)
- Phase 1 Core + Sandbox substrate: DynamoDB, grant/audit S3, SQS, IAM roles, seeded grant store
- Phase 2 broker vertical slice: schema → policy → claim → AUDIT OPEN → scoped execute →
  AUDIT CLOSE
- Phase 3 runtime loop: VERIFY → OBSERVE → LEARN → StubReasoner → DECIDE → SQS, with
  runtime and broker Lambdas.
- Phase 4 liveness: `heartbeat.ping()` at the end of every cycle, silence watch, DLQ
  alarm, expired-lease metric. Runtime cannot mute the monitor.
- Phase 5 adversarial validation: `D1`–`D8` live, CloudTrail session-name join, cost per
  cycle measured (~$0.000043 on the stub).
- Phase 6 model insertion: `ModelReasoner` adapter, versioned prompt, Amazon Bedrock
  (GPT-5.6 Terra) via IAM. No model API key. Live Lambda remains `REASONER=stub`.
- Phase 7a stub qualification: 100 consecutive EventBridge cycles on the stub. Wake is
  `DISABLED`. Live `REASONER` remains `stub`. Phase 7b (Terra) is **blocked** on AWS
  account verification of Core (`docs/plans/v0/evidence/phase-7b.md`). 0.0 is not closed.

**In progress**

- Rung 0.1 is not started. Next experiment is Phase 7b (Terra), not external research.

**Not yet enabled**

- Live model inference (`REASONER` remains `stub`)
- Autonomous spending
- External communications
- Autonomous venture operation

That last list is the important one. It is the boundary between what exists and what is
merely written down, and it is maintained deliberately so that six months from now
documentation aspiration is not mistaken for implemented capability.

**Lambdas exist. Wake is DISABLED, still on the stub.** `rootstock-runtime`
and `rootstock-broker` run in Core. Only `lambda.amazonaws.com` can assume either role.
IAM negatives: `docs/plans/v0/evidence/phase-1.md`. Broker slice:
`docs/plans/v0/evidence/phase-2.md`. Runtime slice:
`docs/plans/v0/evidence/phase-3.md`. Liveness:
`docs/plans/v0/evidence/phase-4.md`. Adversarial validation:
`docs/plans/v0/evidence/phase-5.md`. Model insertion:
`docs/plans/v0/evidence/phase-6.md`. Qualification:
`docs/plans/v0/evidence/phase-7.md`.

---

## The version ladder

Each rung adds exactly one class of capability. Nothing on a rung is attempted before the
rungs beneath it work.

| Rung | Adds | Status |
| --- | --- | --- |
| **0.0** | Organism — wake, observe, decide, invoke one sandbox capability, record, sleep | 7a PASS (stub); 7b PENDING (Terra) |
| **0.1** | Autonomous research | not started |
| **0.2** | Autonomous sandbox building | not started |
| **0.3** | Autonomous deployment | not started |
| **0.4** | External interaction | not started |
| **0.5** | Bounded spending | not started |
| **0.6** | First venture | not started |
| **1.0** | First dollar without human operational action | not started |

Money arrives at 0.5, deliberately late. Everything before it is unpaid rehearsal, which
keeps the expensive failure modes unreachable during the rungs where the system is least
proven.

**Next milestone — 7b:** 10–20 supervised Terra cycles, currently blocked on AWS
account verification of Core. Rung 0.0 closes only after 7b. Do not start 0.1
research first. Do not enable EventBridge to wait.

---

## Repository

| Path | Contents | Authority |
| --- | --- | --- |
| `docs/brainstorm/` | Exploration | Reasoning, not decisions. Contradictions allowed |
| `docs/design/` | Committed architecture | **Normative.** Contradictions are bugs |
| `docs/plans/` | Ordered implementation strategy | Expected to change as we learn |
| `operations/` | What actually exists, as built | Record of reality |

Operator-local files (gitignored): copy `infra/accounts.example.json` to
`infra/accounts.json` and `infra/v0/terraform.tfvars.example` to
`infra/v0/terraform.tfvars`. Live account ids and notification addresses stay off the
public tree.

The layering is the point:

> **Design says what must be true. Plans say how we intend to make it true. Implementation
> and tests prove whether it actually is.**

A plan being rewritten means we learned something about execution. It does not mean the
architecture changed — that requires editing `docs/design/`, deliberately. Where design and
brainstorm disagree, design wins.

### Start here

- [`docs/design/00-system-boundaries.md`](docs/design/00-system-boundaries.md) — trust
  zones, the deterministic/model split, and the architectural requirements (`AR-*`) that
  must hold even if the runtime is adversarial
- [`docs/design/01-rootstock-v0.md`](docs/design/01-rootstock-v0.md) — the 0.0 organism and
  its loop
- [`docs/design/02-capability-model.md`](docs/design/02-capability-model.md) — the
  request → policy → executor → result pipeline, and the vocabulary of Rootstock's autonomy
- [`docs/design/03-runtime-and-broker.md`](docs/design/03-runtime-and-broker.md) — the
  protocol between the two halves, replay safety, and the IAM graph
- [`docs/plans/v0/2026-08-26-rootstock-v0.md`](docs/plans/v0/2026-08-26-rootstock-v0.md) —
  the build order for 0.0, in eight phases with exit criteria
- [`operations/aws-setup.md`](operations/aws-setup.md) — the AWS organization as built
- [`docs/brainstorm/README.md`](docs/brainstorm/README.md) — the conceptual notebook

---

## How autonomy is expressed

Rootstock never "has AWS." It has named capabilities, each granted, scoped, priced, logged,
and revocable:

```text
sandbox.s3.create_bucket
sandbox.lambda.deploy
sandbox.logs.read
web.search
memory.read
memory.write
```

Every invocation passes through the same pipeline, split across two processes that cannot
substitute for each other:

```text
rootstock-runtime   model access, no side-effect authority
        │           CapabilityRequest
        ▼
rootstock-broker    schema → dedupe → policy → audit → execute
        │           credentials, no model access
        ▼
CapabilityResult    ALLOW | DENY | REQUIRE_APPROVAL → outcome, cost, audit id
```

The model proposes. It never executes, never holds a capability credential, and never
decides whether it was permitted. "What can Rootstock do?" is answered by enumerating
granted capabilities, not by describing a model's abilities.

---

## Prove it without AWS

Requires Python 3.12 and [`uv`](https://docs.astral.sh/uv/). Initial install needs network.
After that, the unit suite needs no AWS credentials, account map, or SSO session.

```sh
uv sync --extra dev
uv run pytest -q
```

That run uses `infra/accounts.example.json` (placeholder account ids `111111111111` and
`022222222222`). Live and destructive tests are deselected by default. They talk to a real
organization and are not part of the proof.

To look at Terraform without targeting an account, copy the example map first:

```sh
cp infra/accounts.example.json infra/accounts.json
terraform -chdir=infra/test-env init -backend=false
terraform -chdir=infra/test-env validate
```

Do not `apply` the example ids.

## Ownership

Created and operated by Sean Wylie, doing business as Wise Kids Studios. Rootstock is a
software project, not a legal person.

Legal ownership, banking, the AWS Management account, domain registrar root, and emergency
shutdown remain permanently human and are never delegated.
