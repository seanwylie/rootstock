# Phase 4 — Liveness

> **Verdict: complete.** All four exit criteria passed. `heartbeat.ping()` is the only
> outbound HTTP call site. Killing the runtime makes the silence watch report `silent=true`.
> The runtime cannot disable, extend, or delete the monitor (IAM simulate). A poison SQS
> message reaches the DLQ and the DLQ alarm enters `ALARM`. Ready for Phase 5.

## Commit / revision

```text
branch          main
base commit     8f7cbeb  ("Record Phase 1 substrate and the Phase 2 broker slice.")
working tree    uncommitted — Phase 3 runtime + Phase 4 liveness
terraform       infra/v0, local state (not committed)
```

## Environment

```text
Python          3.12.3
uv              0.11.6
Terraform       1.9.8
AWS CLI         2.33.12
OS              Linux 7.0.0-30-generic
live test       2026-08-26T15:41:31Z  make v0-liveness-live  (3 passed in 216.57s)
IAM negatives   2026-08-26T15:16Z     make v0-assert-iam
```

## Tests run

```text
ruff check / format                 pass
mypy --strict                       pass (51 source files)
pytest -m 'not destructive and not live'   pass (102 passed, 6 live deselected)
terraform fmt / validate            pass
make v0-assert-iam                  pass (including monitor-mute negatives)
make v0-liveness-live               pass (3 passed)
```

## Destructive tests run

**D1 live**, not yet registered in `tests/destructive/runner.py` (that registry is still
Phase 5's job). The body is `tests/live/test_phase4_liveness.py::test_live_d1_kill_runtime_silence_alerts`:
set silence window to 5s, ping via a noop cycle, set runtime reserved concurrency to 0,
invoke the watch, assert `silent=true`. Restore concurrency and window.

## AWS context resolved

```text
profile     rootstock-core
zone        core
account     111111111111
```

Wake rule `rootstock-runtime-wake` remains `DISABLED`. Silence watch
`rootstock-silence-watch` is `ENABLED` at `rate(1 minute)`.

## Exit criteria

| # | Criterion | How | Result |
| --- | --- | --- | --- |
| 1 | Kill runtime → alert within the window (`D1`) | Live: reserved concurrency 0; watch returns `silent=true` | pass |
| 2 | Runtime cannot silence, extend, or delete the monitor | IAM simulate: DisableRule, DeleteAlarms, DisableAlarmActions, UpdateFunctionConfiguration, DeleteFunction, PutItem on heartbeat table, PutParameter on the window | pass |
| 3 | Poison message → DLQ and alarm | Live: mapping disabled, maxReceiveCount=1, message redriven, alarm `rootstock-dlq-messages` → `ALARM` | pass |
| 4 | Exactly one outbound HTTP call site | Unit: no `http_request`; single `urlopen(` in `heartbeat.py` | pass |

## Observed results

- `heartbeat.ping()` takes no arguments. The URL is `HEARTBEAT_URL` on the runtime Lambda
  (Function URL + token). Every cycle outcome pings: enqueue, skip, halt, noop.
- The sink Lambda writes `last_ping` on `rootstock-heartbeat`. The runtime role has no
  `PutItem` on that table, so it cannot fake liveness except by HTTP GET of the configured
  URL.
- Expired-lease halt emits `Rootstock/ExpiredLease` via `cloudwatch:PutMetricData`
  (namespace-conditioned). Alarm `rootstock-expired-lease` exists.
- Silence window SSM `/rootstock/heartbeat-silence-seconds` defaults to 604800 (7 days)
  while wake is disabled, so the watch does not sit in `ALARM` during development. D1
  shortens it for the test and restores it.

## Cost

Function URL pings and one DLQ message per live run, then drained. Negligible. No model.

## Deviations from plan

1. **The dead-man's-switch is in Core, not a third-party host.** Design asked for a monitor
   outside AWS (healthchecks.io or similar) so a Core compromise cannot silence it. What
   shipped is a sink + watch with a **different role than the runtime**. That satisfies
   "not the runtime" and the mute-negatives. It does **not** survive destruction of the
   Core account. Pointing `HEARTBEAT_URL` at a healthchecks.io ping URL is a configuration
   change; `ping()` does not care. Recorded as a design finding.
2. **Poison redrive was tested with the mapping disabled.** Lambda event source mappings
   raise visibility to at least the function timeout (90s), so a 5-second visibility and
   `maxReceiveCount=2` still took too long and raced the broker. The live test disables
   the mapping, receives once, and lets SQS redrive. The broker still returns
   `batchItemFailures` for `not-json` (handler code). Production redrive remains
   `maxReceiveCount=5`, visibility 180s.
3. **Wake stays DISABLED.**

## Design findings

### Function URL `AuthType=NONE` needs `lambda:InvokeFunction` as well as `InvokeFunctionUrl`

A resource policy allowing `lambda:InvokeFunctionUrl` with `lambda:FunctionUrlAuthType=NONE`
and `Principal=*` still returned HTTP 403 until `lambda:InvokeFunction` for `Principal=*`
was added. The ping token remains the real gate.

### A CloudWatch alarm in Core shares a blast radius with the thing it monitors

This is the finding `03-runtime-and-broker.md` already stated. Phase 4 implemented the
in-account detector so D1 is testable without a vendor account. A third-party DMS remains
the production hardening for AR-10; it is not required to start Phase 5, but it should be
the URL before unattended wake is enabled.

## Blocker encountered

Function URL 403 blocked the first D1 run (`last_ping` missing). Adding
`AllowPublicHeartbeatInvoke` unblocked pings (HTTP 204). Poison-to-DLQ failed until the
second receive after visibility expiry (SQS moves on the *next* receive after
`maxReceiveCount` is hit).

## Ready for Phase 5

Yes. D1 has a live body. The destructive runner still lists D1–D8 as unimplemented;
Phase 5 fills those bodies against the existing registry. Do not enable the wake rule.
