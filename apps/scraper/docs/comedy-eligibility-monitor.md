# Source comedy quality monitoring

The monitor measures source trust using persisted event observations. It does
not decide that comedy never occurs at a venue. A downgrade removes a feed's
comedy-only presumption so that individual events require screening; the venue
and source remain available for genuine comedy.

## Provisional operating thresholds

The initial window is 30 days, with all three conditions required for a downgrade
recommendation:

- At least 20 distinct event candidates in the window.
- At least five strong negative events.
- Strong negative events comprise at least 25% of those candidates.

| Setting | Default |
| --- | --- |
| `COMEDY_MONITOR_WINDOW_DAYS` | `30` |
| `COMEDY_MONITOR_MIN_EVENTS` | `20` |
| `COMEDY_MONITOR_MIN_REJECTIONS` | `5` |
| `COMEDY_MONITOR_REJECTION_FRACTION` | `0.25` |
| `COMEDY_MONITOR_AUTO_DOWNGRADE` | `0` |

Repeated scrape observations of one event must not count as new events. The
denominator is the number of observed candidates, including uncertain events;
missing lineups are reported separately and never counted as negative evidence.
The window uses observation recency, not the event's performance date; a future
event repeatedly seen on a calendar remains one observed candidate.

A strong negative comes from the deterministic baseline's rejection with valid
explicit non-comedy event evidence, or a fully observed, blocked-only lineup
without a valid canonical-parent rescue. An incomplete blocked lineup is not a
strong negative. Positive/negative conflicts remain uncertainty; an accepted
structural-label exception is not contamination. Model and human outcomes must
not silently replace the baseline evidence used for this signal.
The baseline also ignores the source's own comedy-only presumption, so trusted
status cannot count as evidence that the source remains trustworthy.

Blocked-performer concentration and lineup coverage are separate reported
metrics, with their own denominators. They are not additional downgrade triggers.
Neither unblocked names nor a zero blocked ratio establish that events are comedy.

| Report metric | Numerator | Denominator |
| --- | --- | --- |
| Acceptance/rejection/uncertainty | Baseline decisions in that category | Distinct observed events |
| Strong rejection | Baseline rejects meeting the strong-evidence guard | Distinct observed events |
| Missing/partial/observed lineup coverage | Events with that lineup status | Distinct observed events |
| Any lineup coverage | Events with performer observations | Distinct observed events |
| Blocked appearances | Parent-resolved blocked performer appearances | Resolved blocked or unblocked appearances |
| Unresolved appearances | Unknown or conflicting performer observations | All observed performer appearances |
| Blocked-only events | Complete lineups containing only blocked performers, excluding accepted structural exceptions | Events with any lineup |

Zero denominators produce a null fraction, not a zero contamination claim. Each
event's canonical performer identities are deduplicated by the classifier before
appearance aggregation; a root and its alias do not count twice in the same event.

The minimum event count prevents a few isolated bookings from changing source
trust. The minimum negative count prevents very small absolute counts from
triggering a percentage rule. The 25% threshold is an initial operational choice,
not a measured error-rate guarantee. Tune it against independently reviewed
source-level observations during TASK-4158 rollout.

## Pilot evidence and its limits

The retained TASK-4151 baseline is in
[`audits/task-4151-comedy-eligibility-baseline.json`](audits/task-4151-comedy-eligibility-baseline.json),
with methods and caveats in
[`audits/task-4151-comedy-eligibility-audit.md`](audits/task-4151-comedy-eligibility-audit.md).
That October 10 snapshot contains 142,375 retained shows, of which 72,697
(51.06%) have no lineup. Parent resolution rescues 292 blocked alias appearances
across 75 venues. These observations support explicit coverage reporting and
parent-aware identity handling.

Harvelle's Santa Monica has 248 retained shows, but only 40 with lineups. Nine
shows are blocked-only. Its upcoming sample has 51 shows, eight lineups, and no
blocked appearances. This does not establish a clean comedy calendar: most
upcoming events lack lineup evidence. A source can still require event screening
when a lineup-based signal cannot establish contamination.

Within the baseline's **selected** 70 majority-blocked visible venues, a minimum
of 5, 10, 20, or 30 lineup-bearing events leaves 36, 30, 21, or 12 historical
candidates respectively. This sensitivity check illustrates why sparse samples
need guards. It does not calibrate the chosen negative-event threshold: these are
biased venue aggregates across all retained history, not rolling source samples
with independently verified labels. Historical source attribution was inferred
from last-writer metadata and is not exact feed provenance.

The read-only production pilot for TASK-4157 found zero staged candidates,
observations, decisions, and reviews; all 2,887 sources were `unreviewed/off`.
Consequently there is no live staged sample from which to estimate monitor
precision, false alarms, or an empirical 30-day threshold. Synthetic boundary
tests below verify rule behavior only. No model API evaluation is involved.

## Executed synthetic boundary checks

From `apps/scraper`:

```sh
PYTHONPATH=src:. .venv/bin/python3 -m pytest \
  tests/integration/test_comedy_eligibility_monitor_pilot.py -q -s
```

The test constructs baseline decisions with the real parent-aware classifier,
then invokes the actual monitor aggregation and recommendation functions. Its
executed result was **2 passed**. The printed boundary matrix was:

| Synthetic sample | Distinct events | Downgrade recommended |
| --- | ---: | --- |
| All events strongly negative, sample below minimum | 19 | No |
| Four strongly negative events | 20 | No |
| Five strongly negative events | 20 | Yes |
| All lineups missing; no event-type evidence | 20 | No |
| Blocked aliases resolved to visible canonical parents | 20 | No |
| Incomplete blocked lineups | 20 | No |
| Accepted structural-label exceptions | 20 | No |
| Positive comedy evidence conflicting with blocked lineups | 20 | No |
| Explicit music evidence, even without lineups | 20 | Yes |

A separate check repeats one negative event 25 times: it still counts as one
event and cannot satisfy the sample minimum. These checks make no database
changes, invoke no model, and do not measure real-world false acceptance or
false rejection. The recommendation is separate from applying a policy change;
automatic downgrade remains off in these defaults.

## Operational handling

From `apps/scraper`, report all enabled trusted or gated sources, or inspect one:

```sh
PYTHONPATH=src:. .venv/bin/python3 scripts/core/monitor_comedy_eligibility.py report
PYTHONPATH=src:. .venv/bin/python3 scripts/core/monitor_comedy_eligibility.py report --source-id 123
PYTHONPATH=src:. .venv/bin/python3 scripts/core/monitor_comedy_eligibility.py history --source-id 123
```

`report` persists deduplicated operational reports but never changes source policy,
even if automatic downgrades are configured for the ongoing scraper. `history`
reads recorded reports and transitions. With no enabled trusted or gated sources,
the all-source command reports `no_monitored_sources`; this is not a health grade.

Monitoring remains active for broadly ingested `comedy_only` sources even when
their publication gate is off. Missing telemetry is a coverage gap, never a
healthy result. Reporting must include trusted sources with zero observations so
operators can distinguish an empty or failed feed from observed clean events.
Such sources carry the reason `no_observations_telemetry_gap`.

Automatic downgrades are disabled by default. An explicit opt-in permits a
threshold breach to change the source to `mixed/enforce`. This changes publication
behavior: uncertain and rejected events are withheld until eligible or reviewed.
The source remains enabled and venue visibility is unchanged. Inspect the
reported evidence and samples before enabling this operational action.

An operator can explicitly apply a qualifying downgrade without enabling ongoing
automatic changes:

```sh
PYTHONPATH=src:. .venv/bin/python3 scripts/core/monitor_comedy_eligibility.py apply --source-id 123
```

To restore a recorded transition, use its transition ID and the current policy
version shown in history:

```sh
PYTHONPATH=src:. .venv/bin/python3 scripts/core/monitor_comedy_eligibility.py rollback \
  --transition-id 456 --expected-version 8 --actor operator-name \
  --reason 'Reviewed the source evidence and restoring the prior configuration'
```

The numbers above are placeholders, not production targets. Rollback refuses a
policy that changed after the transition. Previously rolled-back evidence is
suppressed so an unchanged observation set cannot immediately reapply the same
downgrade.

Transition history records the evidence and prior configuration. Unchanged
observations must not generate repeated alerts or repeated policy changes.
Rollback is an explicit operator action, not an automatic upgrade when a rolling
window expires or contamination disappears. A rollback does not repair identity
data, delete staged evidence, or claim the source is now comedy-only.

Before broad rollout, collect a source-attributed pilot window, independently
review both flagged and unflagged events, check coverage and parent resolution,
and document threshold adjustments. Absence of sufficient data must preserve the
sparse-data guard rather than weaken it to force a result.
