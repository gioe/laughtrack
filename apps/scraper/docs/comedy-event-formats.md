# Comedy content and public audience formats

The public live-show feed serves audiences attending live performances. A comedy
class or comedy-film screening can contain comedy without being a live audience
show. Format exclusions must never count as evidence that the venue never hosts
comedy, or as a correctly detected non-comedy event in precision reports.

The deterministic `comedy-audience-formats-v1` family records the actual offering
separately from comedy content and the existing identity decision. Decisions retain
`content_status` (`comedy`, `non_comedy`, `conflicting`, `unknown`), `audience_format`,
`format_disposition`, and the effective versioned `format_policy`. The final
accept/reject/review decision additionally respects existing identity, availability
and genre guards. A format allowance cannot override a genre or identity rejection.

| Evidence about this event | Audience format | Default disposition | Reason |
| --- | --- | --- | --- |
| Explicit live performance, graduation show or student/class showcase | `live_performance` | `allow` | An audience performance, even when the performers are students |
| Standalone film/movie screening or television viewing | `screening` | `exclude` | Recorded content is not a live performance; genre remains independent |
| Explicit class enrollment, instructional course or workshop instruction | `instruction` | `exclude` | The offering is participation/training, not watching a public show |
| Corporate/networking mixer | `mixer` | `exclude` | Networking is not live performance billing |
| Screening combined with a live performance, or instruction/mixer plus performance | `mixed` | `review` | A reviewer must resolve the public audience offering |
| Workshop without explicit enrollment/instruction; unqualified variety/drag/burlesque/magic offering | `ambiguous` | `review` | These words do not establish either non-comedy or an eligible comedy performance |
| No supported format evidence | `unknown` | `allow` | Preserve the existing genre/identity decision; this does not itself accept the event |

Configuration is source-owned in `comedy_review_evidence.format_policy`, with
`version: "comedy-audience-policy-v1"` and an optional `dispositions` object mapping
the formats above to `allow`, `exclude`, or `review`. Missing entries inherit the
table defaults. Unknown keys, values or versions fail validation. Updates use the
existing reviewed source-policy save path: its database trigger increments
`comedy_policy_version` when the JSON changes. No migration, production policy
update or enforcement activation is part of this task. The complete effective
format policy is retained in each staged decision for comparison and replay.

Only bounded event titles and validated, collected same-event detail statements
supply format evidence. Unicode normalization affects matching, not exact saved
citations. Venue branding, biographies, navigation, quoted titles, hypothetical or
negated offerings, other dates and rooms are not positive offering evidence. The
existing event-detail identity/selector/URL checks continue to apply. An arbitrary
`Show.description` is not trusted evidence. Broad words such as class, movie,
workshop, drag, burlesque or magic alone never mean non-comedy. A showcase phrase
protects only its own performance component; separate enrollment or screening
offerings still make the event mixed/reviewable.

Comedy content remains affirmative for explicit comedy/improv instruction or
comedy-film billing, even when format excludes the event. A generic screening or
corporate mixer has unknown genre without further evidence. Movie Pass alone is
unknown; an explicit improvised movie performance is a live comedy offering.
Bare student/class showcases establish live performance, not necessarily comedy;
comedy/improv/stand-up context or other event evidence must establish genre.

`off` preserves existing publication without staging; `shadow` stages decisions
and evidence while preserving publication; `enforce` withholds rejected/review
candidates before public entity writes. Existing human review remains intentional
authority and preserves the deterministic content/format metadata. Optional model
enrichment cannot promote format holds; no provider call is required.

## Exposed development examples

These examples come from the immutable October 11 search audit, specifically
[`baseline-v1/triage/titles.txt`](audits/comedy-search-rules/baseline-v1/triage/titles.txt).
They are exposed development cases, not blind validation or inferred gold labels:

- Group 23: **Stand Up Graduation Show**; groups 161–184 include Brooklyn Comedy
  Collective class shows; group 1010: **101 COMEDY CLASS SHOWCASE**; group 1822:
  **Jeff Justice Comedy Workshoppe Graduation Show**. Preserve their performance
  formats instead of rejecting the class/workshop words.
- Group 1801: **Movie Pass** at The Pack Theater. The title alone does not establish
  screening; explicit improvised-performance evidence preserves live comedy.
- Group 1199: **Corporate Mixer - Learn How Improv Can Help Your Business!**.
  Instruction/networking format is separate from its comedy-content assessment.
- Group 29: **The Addams Family - 7pm - Classic Movie Nights!**; group 98:
  **An Evening With John Cusack (featuring Screening Of High Fidelity)**. Recorded
  viewing and potentially mixed appearances require format treatment, not assumed
  non-comedy labels.
- Groups 69–70: comedy-writing/improv workshop series; group 374: **THE WORKSHOP
  presented by Commonwealth Comedy Club**. The latter name alone does not prove
  instructional enrollment.

TASK-4166 must report format exclusions/reviews separately from non-comedy
precision, keep unknowns explicit, and compare against the preserved baseline.
The frozen archive is unchanged. Independent rollout validation remains TASK-4160.

Focused offline checks: `PYTHONPATH=src:. .venv/bin/python3 -m pytest
tests/integration/test_comedy_event_formats.py -q` from `apps/scraper`.
