# Source trust review — October 11, 2026

**Recommendation: do not grant Goodnights source 192 `comedy_only` trust.**
The current evidence supports comedy at many individual events, but does not
establish a comedy-only feed. Keep Harvelle's sources 527 and 595 subject to
event-level review. No policy, identity, venue visibility or inventory changes
were made for this review.

## Current configuration and population

Read-only configuration verification found all three sources enabled,
`unreviewed/off`, policy version 3, with `seatengine_event_details=true`.

| Source | Venue / club | SeatEngine venue | Live occurrences | Native groups |
| --- | --- | --- | ---: | ---: |
| 192 | Goodnights / 61 | 53 | 216 | 86 |
| 527 | Harvelle's Santa Monica / 475 | 450 | 50 | 50 |
| 595 | Harvelle's Long Beach / 476 | 451 | 84 | 37 |

The provider calendars were fetched through the scraper's SeatEngine HTTP
client at 2026-10-11 16:15:01 UTC, without transformation or classification.
All 173 native groups had already appeared in TASK-4158 inputs and full-feed
classifier output. There are **zero genuinely new native groups**. Goodnights'
26 groups outside the 60-group frozen label sample are previously exposed,
not untouched validation. The saved raw snapshot SHA-256 is
`11f691555303ab396acb4b10d3aaeaec2d912fbd5f592007bf650de1d1919089`.

## Goodnights programming evidence

The frozen review covered 60 of 86 groups and 153 of 216 occurrences. It found
13 comedy groups (28 occurrences), one non-comedy group (one occurrence), and
46 unknown groups (124 occurrences). The other 26 groups, representing 63
occurrences, were not independently labeled. These denominators describe the
whole fetched population and reviewed subset separately; they do not certify
the remaining program by extrapolating the venue's name or performer careers.

The directly reviewed exception is event **143136**, occurrence **386016**,
[Rocky Horror Drag Brunch](https://www.goodnightscomedy.com/shows/386016).
The event description bills a themed drag show with musical numbers and
audience participation, without affirmative comedy-performance evidence. Its
frozen `non_comedy` label remains unchanged. Drag performance alone does not
prove either comedy or its absence; this is the recorded event-specific
assessment, not a general rule about drag. It is sufficient reason not to
convert the whole feed into trusted comedy on the present evidence.

The 46 unknown labels also remain unchanged. Many reviewed pages describe
performer biographies or credits without clearly identifying the current
performance format. Database membership, popularity and venue branding do not
resolve that gap. An unreviewed group is not presumed comedy or non-comedy.
No additional independent labels were created for the 26 unsampled groups.

There is strong event-level comedy evidence for the 13 confirmed groups: an
open mic advertising local comedians, the Ladies Laugh Lounge holiday lineup,
explicit stand-up engagements, and current-show or tour descriptions. The
[adjudication artifact](task-4160-adjudications.json) records exact event URLs,
short evidence excerpts, identity status and scoped recommendations. Some
recommendations require contextual operator judgment; they are not a request
to make broad biography keywords authoritative.

## Mixed venues and identity boundaries

Harvelle's Santa Monica had 42 non-comedy and eight unknown groups in its
50-group census, with no confirmed comedy group available to establish
retention. Long Beach has confirmed comedy mixed with substantial non-comedy
programming. Neither calendar supports blanket source trust or a conclusion
that comedy never occurs at the venue.

The remaining known comedy misses consist of six groups whose blocked names
are structural show/format labels and 17 groups lacking automatically recognized
current-event evidence. No observed lineup in this set identifies a blocked
actual person. Unknown identities remain unknown. Preserve existing deny-list
and visibility records; event approval does not make a show title into a person.
Two Goodnights misses already have valid canonical parent resolution, which
repairs identity but does not independently establish comedy performance.

Recommendations are not applied reviews. Refresh staging under the current
policy before preparing an attributed review. The preview and application must
bind candidate generation, latest review version, payload, baseline identity
fingerprint and policy version. Old version-2 observations cannot authorize a
version-3 action. Later publication must use the normal fenced gate, with no
direct public writes or global identity exceptions.

## Decision and next evidence

Keep all three sources off or shadow until their prospective thresholds pass.
Source-level trust could be reconsidered only with a documented feed boundary
that excludes programming exceptions, complete event-format evidence and fresh
validation of that boundary. Do not silently discard the drag-brunch exception
or unknowns to obtain a comedy-only denominator.

Freeze new native event groups and independent labels before classifier
outcomes. A new-source cohort can provide additional evidence, but cannot
replace source-specific Harvelle retention evidence. TASK-4158's no-go and
known-label development results remain intact. This review used no model calls
and performed no database writes.
