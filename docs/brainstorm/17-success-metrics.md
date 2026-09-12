# 17 — Success Metrics

> Status: Draft.

Avoid optimizing solely for revenue. Revenue is the most legible metric and one of the least
informative — a venture can grow revenue while destroying capital, and Rootstock optimizing
for it would be a specific, predictable failure (`14`).

Metrics here serve two different purposes that should not be confused: **operating metrics**
tell Rootstock what to do next, and **experiment metrics** tell the operator whether the Rootstock
concept is working at all. During the bootstrap rungs the second set matters far more.

## The north star

> **Profit generated per human minute of intervention.**

```text
north_star = net_income / human_intervention_minutes
```

It captures the entire thesis in one ratio. A system that earns $500/month requiring 40
hours of the operator's attention has failed. A system earning $80/month requiring 20 minutes is
succeeding, and it is the one that scales.

Eventually Rootstock should drive the denominator toward zero. Two cautions:

- **Undefined is not infinite.** Zero interventions with zero profit is not a win.
- **The denominator counts intervention, not oversight** (`15`). Reading a digest is not
  intervening. Answering an approval, debugging, and handling escalations are.

Before 1.0, when profit is zero by definition, track the denominator alone: **human
minutes per week.** It is the metric that will most honestly tell the operator whether this is
working, well before any revenue exists.

## Survival

```text
runway              months at current burn, net of revenue
monthly_burn        shared + venture fixed + baseline inference
reserve_ratio       treasury / reserve requirement
cash_position       absolute, from the ledger (FIN-4)
```

Runway is the metric with real teeth (FIN-6). During bootstrap it is misleading for the
reasons in `03`, and should be reported alongside an explicit "subsidized" flag rather than
implying a solvency Rootstock does not have.

## Economic performance

```text
MRR                     recurring revenue
net_income              after ALL costs, including operator inference
gross_margin            per venture and portfolio
contribution_margin     revenue - directly attributable costs
ROIC                    return on invested capital
capital_efficiency      revenue generated per dollar deployed
payback_period          months to recover invested capital
```

**Net income must include operator inference.** Excluding the cost of running Rootstock
itself is the easiest way to report a profitable portfolio that consumes cash — and it is
the specific meta-failure in `14`. If the organization costs more than the ventures earn,
that must be visible in the headline number, not buried in shared costs.

## Portfolio

```text
active_ventures
profitable_ventures
dead_ventures
median_time_to_validation
median_time_to_first_revenue
kill_rate                    fraction of ventures killed
mean_capital_per_venture
portfolio_concentration      revenue share of largest venture
```

Two of these deserve interpretation rather than optimization.

**Kill rate should be high.** A low kill rate means Rootstock is not experimenting or not
killing — both bad. Something like 70–80% would be healthy for early-stage bets. But it must
never become a target, or ventures get killed to improve the statistic (`14`).

**Median time to validation is the real learning metric.** It measures how fast Rootstock
converts capital into information, which is the actual engine of a venture studio. Improving
it improves everything downstream.

## Autonomy

```text
human_interventions_per_month     count, by category (15)
human_minutes_per_month           the north-star denominator
approval_requests                 count and mean latency
approval_denial_rate
autonomous_decisions              count of consequential decisions with no human input
escalation_rate                   escalations per customer interaction
uptime_without_intervention       longest continuous unassisted operation
```

`uptime_without_intervention` is a good headline. "Rootstock ran for 23 days without needing
the operator" is more meaningful than most financial figures at this stage.

**Approval denial rate is diagnostic in both directions.** Near zero means Rootstock is only
asking for things it knows will be approved, or the operator is rubber-stamping. High means
Rootstock's judgment is miscalibrated against the constitution. Somewhere in the middle
means the gate is doing real work.

## Learning

```text
hypotheses_tested
institutional_lessons_recorded
lessons_reused                    decisions citing a prior lesson
repeat_failure_rate               same mistake twice
claim_staleness                   share of active claims past expiry
decision_calibration              |expected - actual| across decisions (13)
```

**`decision_calibration` and `repeat_failure_rate` are the two that matter most**, because
they measure whether Rootstock is actually an organization that learns rather than one that
merely accumulates records.

A repeat failure is a direct indictment of `06`. If Rootstock makes the same mistake twice,
institutional memory did not work, regardless of how many lessons it contains.

## Reliability

```text
venture_uptime
incidents                          count and severity
invariant_violations               should be zero
ledger_divergence                  should be zero
orphaned_resources_found           should be zero (OPS-1)
audit_completeness                 actions with a decision record / total actions
mean_time_to_detect
```

`invariant_violations`, `ledger_divergence`, and `audit_completeness` are **pass/fail, not
trends.** A nonzero invariant violation count is not a metric that needs improving; it means
the system is broken as defined in `01`.

## Anti-metrics

Metrics deliberately *not* optimized, watched precisely because optimizing them would cause
harm. This section exists because Goodhart's law is not patchable, only monitored (`14`).

| Metric | Why not a target |
| --- | --- |
| Gross revenue | Can rise while capital is destroyed (FIN-5) |
| Number of ventures launched | Rewards activity over judgment |
| Lines of code, deploys, commits | Rewards motion |
| Traffic | Trivially gamed, and the road to content farming |
| Customer count | Worthless without margin |
| Lessons recorded | Rewards volume; degrades retrieval (`06`) |
| Low intervention count | Achievable by avoiding approval-worthy actions (`15`) |
| Runway | Maximized by doing nothing |
| Kill rate | Gameable in both directions |

The general defense: **no single metric is a target, and every metric has a named
counter-metric.** Revenue is paired with margin; intervention count with autonomous
decisions; kill rate with time-to-validation; runway with capital deployed.

## Metrics by phase

What to actually watch, and when.

**Bootstrap (0.0–0.4, pre-revenue).** Did the loop run? Human minutes per week. Invariant violations.
Audit completeness. Time from boot to first deployed property. Whether ledger matches
reality. Money is not the metric here.

**Post-1.0 (first revenue).** Time to first dollar. Ledger accuracy against providers.
Contribution margin. Support escalation rate. Uptime without intervention.

**Post operating break-even.** North star. ROIC. Median time to validation. Repeat
failure rate. Portfolio concentration.

**Mature.** North star trend. Capital efficiency. Decision calibration. Longest unassisted
run. Whether retained earnings are compounding.

## Reporting

The weekly digest (`13`) leads with: runway, north star (or its denominator), venture
status changes, decisions with capital at risk, variances from expectation, and anything
needing attention.

**Do not report every metric every week.** A digest with forty numbers is a digest nobody
reads, and an unread report has the same value as no report while creating a false sense of
oversight.

## Open questions

- How is `human_intervention_minutes` actually measured? Self-reported by the operator is
  unreliable; inferred from approval and escalation events undercounts thinking time.
  Probably approximate and consistently biased is fine, as long as the bias is stable enough
  for the trend to mean something.
- Should Rootstock see its own metrics? Mostly yes — it needs them to operate. But showing
  it the north star invites optimizing the denominator in the illegitimate ways listed in
  `15`. Leaning: Rootstock sees operating metrics, the operator alone sees the experiment metrics.
- What is the single number that would make the operator say "this worked"? Possibly: months of
  continuous operation with positive net income and under 30 minutes per month of
  intervention.
- How to measure institutional knowledge value? `lessons_reused` is a proxy and a weak one.
