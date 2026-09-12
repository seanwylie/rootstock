# 02 — Autonomy Model

> Status: Draft. Defines what "autonomous" means, in degrees.

## Why not binary

"Is Rootstock autonomous?" is a bad question. It produces bad answers in both directions:
either an overclaim that ignores the approval gates, or an underclaim that ignores how much
happens without a human.

The useful question is: **for this specific capability, at this moment, how much authority
does Rootstock hold?** Autonomy is a per-capability, revocable, earnable property. It is
never a property of the model.

This follows from the second architectural principle: autonomy is granted through
capabilities, not assumed through intelligence. A more capable model does not become more
autonomous. It becomes a better candidate for a grant that a human still has to make.

## The levels

```text
L0 — advisory
     Rootstock recommends. A human performs the action.

L1 — delegated execution
     Rootstock performs specifically approved tasks. Approval is per-instance.

L2 — bounded autonomy
     Rootstock acts freely within a defined budget and capability envelope.
     No per-instance approval; the envelope was the approval.

L3 — operational autonomy
     Rootstock independently manages an existing venture: operates, supports,
     fixes, tunes, and reports.

L4 — entrepreneurial autonomy
     Rootstock discovers, funds, builds and launches new ventures.

L5 — portfolio autonomy
     Rootstock allocates capital across ventures and retires poor performers
     on its own judgment.
```

Two properties worth naming explicitly:

- **The levels are not a maturity ladder for the system as a whole.** Rootstock will
  permanently sit at L0 for some capabilities (constitutional change) and may reach L4 for
  others (deployment) quite early. There is no state where "Rootstock is at L4."
- **L5 is the real prize and the real risk.** Everything below L5 is Rootstock executing.
  At L5 Rootstock is *deciding what deserves to exist*, which is the entire thesis of `00`
  and the point at which capital allocation quality becomes the binding constraint.

## Capability levels at 1.0

This is the grant table **as it should stand when Rootstock reaches 1.0** (`16`).
`[PROVISIONAL]` throughout — these are opening positions chosen to make the first venture
possible while keeping every irreversible or expensive action gated.

Note that a capability's level and its *availability* are separate things. Most rows below
do not exist at all on the early rungs of the ladder: spending is not granted until 0.5,
customer support not until 0.4. The level says how much latitude Rootstock has *once the
capability exists*.

| Capability | Level | Available from | Notes |
| --- | --- | --- | --- |
| Research (web, competitive, market) | L4 | 0.1 | Read-only, cheap, low risk |
| Form opportunity theses | L4 | 0.1 | Output is a document, not an action |
| Write and commit code | L4 | 0.2 | To Rootstock-owned repos only |
| Deploy to a venture environment | L3 | 0.3 | Within an authorized venture |
| Provision infrastructure within budget | L2 | 0.2 | Hard cost cap per resource class |
| Spend < $25 | L3 | 0.5 | Attributed, logged, within venture cap |
| Spend $25–$100 | L2 | 0.5 | Within an authorized venture's remaining budget |
| Spend > $100 | L0 | 0.5 | Human approval, per instance |
| Authorize a *new* venture | L1 | 0.6 | See progression below |
| Register a domain (approved TLD list) | L2 | 0.3 | Cost-capped; TLD list is constitutional |
| Set or change pricing | L3 | 0.6 | Bounded by a price floor and ceiling |
| Reply to customer support | L3 | 0.4 | Templates and escalation rules apply |
| Issue a refund < $20 | L3 | 1.0 | Above that, L0 |
| Publish marketing content | L3 | 0.4 | Subject to IDN-2 claim checks |
| Paid customer acquisition | L2 | 0.5 | Daily cap; CAC-based auto-halt |
| Kill a venture | L3 | 0.6 | Killing is encouraged and cheap to do |
| Reallocate capital between ventures | L1 | post-1.0 | Rises to L2/L5 as the ledger proves out |
| Modify a constitutional rule | L0 | never | Permanently. See CTL-3 |
| Grant itself a capability | prohibited | — | CTL-4 |
| Incur debt | prohibited | — | FIN-2 |
| Create another autonomous organization | prohibited | — | CTL-7 |
| Access the root of trust | prohibited | — | CTL-2 |

Note the shape: Rootstock starts near-fully autonomous at *thinking* and *building*, and
heavily gated at *spending* and *committing*. That is intentional. Research and code are
cheap and reversible; money and public commitments are not.

## The progression

Rootstock does not begin at the grant table above. It begins at 0.0 holding almost
nothing — a handful of Sandbox capabilities and memory access (`docs/design/01-rootstock-v0.md`)
— and the table above is where it arrives at 1.0.

The intended sequence once ventures exist:

1. **Authorize the first venture at L1.** Human-approved. This is about debuggability, not
   distrust — the first end-to-end pass will expose a dozen missing rules, and it should do
   so with a human watching.
2. **After the first venture reaches OPERATING**, raise support, pricing, and deployment to
   L3. Rootstock runs the thing it built.
3. **After the first *kill*** — a venture terminated cleanly, with a recorded lesson and no
   orphaned resources (OPS-1) — raise venture authorization to L2 within the exploration
   budget. A system that has demonstrated it can stop is much safer to let start.
4. **After operating break-even**, consider L5 for capital reallocation.

The ordering is deliberate: **the authority to kill is earned before the authority to
create.** A system that can create but not terminate accumulates zombie ventures, which is
one of the more plausible failure modes in `14`.

## How authority changes hands

**Earning.** A level increase requires: a recorded track record against the capability, no
invariant violations in the window, an explicit human grant (CTL-4), and a recorded
rationale. Levels are never raised implicitly through good behavior — a human acts.

**Losing.** A level decrease can be automatic. Any of the following should demote the
relevant capability immediately: an invariant violation, a runway breach (FIN-6), an
unexplained ledger divergence (FIN-4), a security incident, or a decision whose actual
outcome diverges from its expected outcome beyond a threshold.

**Automatic demotion is a feature.** It means the system degrades toward safety without
needing the operator to be awake. See the restricted mode in `15`.

**Expiry.** `[OPEN]` — should grants above L2 carry an expiry requiring renewal? It
guarantees periodic review and prevents authority accumulating by inertia, at the cost of
recurring human effort. Leaning yes for L4 and L5, with a long period.

## Relationship to Argus

Argus already implements a version of this and the vocabulary should stay aligned where
possible. Argus has `AutonomyMode` (`off`, `manual`, `supervised`, `limited`, `active`) plus
rollout tiers 0–4, with numeric caps including `max_cost_per_day`, enforced deterministically
in `argus/autonomy/controller.py` before execution.

Two differences worth noting rather than smoothing over:

- Argus's autonomy is **global to the operator** with per-product permissions layered
  underneath (`argus.policy.yaml` with `yes` / `no` / `confirm`). Rootstock's L0–L5 is
  **per-capability first**. These compose fine, but the mapping is not one-to-one and
  should not be faked.
- Argus governs actions on products that already exist. Rootstock's L4 and L5 have no Argus
  equivalent, because Argus never decides that a product should be born.

The `confirm` permission value maps cleanly onto L1, and the `confirm_once` / `always`
grant responses are a good model for how Rootstock's per-instance approvals should behave.
Worth reusing verbatim.

## What autonomy is *not*

- **Not the absence of oversight.** the operator reads reports at every level. Observation is not
  intervention, and it does not lower the autonomy level (`17` counts intervention minutes,
  not reading minutes).
- **Not unsupervised access to money.** Even L5 operates inside FIN-1 and FIN-6. Portfolio
  autonomy means choosing among allocations, not choosing the size of the pot.
- **Not permanence.** Every grant is revocable, and revocation does not require Rootstock's
  cooperation (CTL-5).
- **Not self-assessed.** Rootstock does not decide it has earned more authority. It may
  present evidence and request a grant, which is a capability request in the Argus sense.

## Open questions

- Should autonomy levels be per-capability, per-venture, or both? A trusted mature venture
  arguably deserves more operating latitude than a three-day-old experiment. Leaning
  "both," with the venture level capping the capability level.
- What is the right demotion blast radius? Does a security incident in one venture demote
  that venture's capabilities, or all of them? Leaning: security demotes globally, economic
  underperformance demotes locally.
- Does time-in-good-standing ever *automatically* promote? Currently no, by CTL-4. Worth
  revisiting only if human grant latency becomes the bottleneck.
