# Plans

An **ordered strategy for getting from the current repository state to conformance with the
architecture in `docs/design/`.**

## What belongs here

Sequencing, phases, exit criteria, build order, and the practical decisions that
implementation forces but architecture does not care about — language, tooling, test
harness, deployment mechanics.

## What does not

Anything that answers *what must be true*. That is architecture, it lives in
`docs/design/`, and changing it is a deliberate act rather than a consequence of finding a
task harder than expected.

## The distinction that makes this directory worth having

> Design says **what must be true.**
> Plans say **how we intend to make it true.**
> Implementation and tests prove **whether it actually is true.**

Plans are expected to be rewritten. A plan that survives contact with implementation
unchanged is more likely to be vague than correct, and revising one carries no implication
that the architecture moved.

The failure this separation prevents: discovering mid-build that a requirement is
inconvenient, quietly relaxing it in the plan, and shipping something that no longer matches
its own design documents. If an `AR-*` requirement turns out to be wrong, that is a real
finding and it belongs in a `docs/design/` edit with reasoning — not a quiet omission from
a task list.

## Layout

Plans are grouped by milestone and dated:

```text
docs/plans/
└── v0/
    └── 2026-08-26-rootstock-v0.md
```

The date is the authoring date, not a deadline. Superseded plans stay in place with a status
marker rather than being deleted — what we expected to be hard, versus what actually was, is
one of the more useful things this project can learn about itself.

## Status markers

```text
[ ] not started
[~] in progress
[x] complete
[!] blocked
[-] descoped, with a reason
```
