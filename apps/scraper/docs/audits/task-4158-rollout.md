# Mixed-feed rollout pilot — October 11, 2026

## Preregistration

Frozen at **2026-10-11 12:45:06 UTC**, before the independent reviewer received
pilot payloads or classifier outcomes. These thresholds are operational go/no-go
guards, not a statistical accuracy guarantee. OpenAI enrichment and automatic
monitor downgrades remain disabled throughout this pilot.

Initial source cohort:

| Source ID | Feed role | Proposed directory/trust treatment |
| --- | --- | --- |
| 527 | Harvelle's Santa Monica, mixed programming | Keep directory eligibility; independently assess event screening |
| 595 | Harvelle's Long Beach, mixed programming | Keep directory eligibility; independently assess event screening |
| 7741 | Empire Strips Back risk-cohort feed, report-only; outside the three-feed SeatEngine fetch pilot | Inspect programming evidence separately; a contamination signal alone does not prove comedy never occurs |
| 192 | Goodnights Comedy Club (club 61; SeatEngine venue 53), selected before blind review | Verify retained comedy coverage; venue branding is not a gold label |

The operator records exact source/venue mapping and selected control before
classification comparison. Policy changes apply to explicit source IDs, not all
sources sharing a venue. Historical TASK-4151 audit ratios identify review
candidates; they are not gold labels or measured source contamination rates.

The initial preregistration text, before control identification and results were
appended, had SHA-256
`9efbaa8ed588d9c666697e8973c47eb5adb17fd62141bca9382b27fe86369861`.
This identifies the original frozen version, not the final updated report file.

## Independent labels and bounded sampling

Use a census for a source with at most 60 distinct native event groups. For a
larger feed, sort groups by earliest upcoming occurrence then native ID, divide
into three date-ordered thirds, and select 20 evenly spaced groups from each
third. Freeze that initial selection and its raw-artifact digest before labels.

The reviewer sees event title, event-specific description/category, source URL,
native group ID, raw performers and occurrence dates. Hide classifier decisions,
resolved block status, and suggested judgments until labels are frozen. Label
each event `comedy`, `non_comedy`, or `unknown`, with a concise evidence excerpt
and URL. Explicit descriptions of the actual performance establish the label.
Venue branding, a familiar performer name, or matching a comedian database row
alone do not. A musician's biography alone does not establish the current event's
format. Ambiguous mixed bills or unsupported listings remain unknown.

After initial labels are frozen, inspect classifier strata: accepts, rejects,
and reviews, including missing lineups and parent-backed exceptions. If any
stratum is absent from the initial sample, add up to ten deterministically
selected events from that stratum; provide their raw payloads to the reviewer
without disclosing the stratum or decision. Freeze their labels before comparing.
Report supplemental strata separately; do not treat a deliberately enriched
sample as an unbiased prevalence estimate. If a required stratum or exception
does not occur, report it absent rather than inventing a live case.

Count distinct native event groups for minimum samples. Report performance
occurrences separately, because repeated performances of one series are not
independent evidence. Repeated scrapes likewise do not enlarge the sample.

## Frozen go/no-go thresholds

Each mixed source must pass independently; successful control or sibling feeds
cannot compensate for a failing source:

1. At least **five independently confirmed comedy event groups**.
2. **Zero confirmed comedy groups withheld**, counting both `reject` and
   `review` as withheld under enforcement. All must be accepted.
3. At least **ten independently confirmed non-comedy event groups**.
4. At least **90% of confirmed non-comedy groups withheld** and **zero accepted
   confirmed non-comedy groups**. Because enforcement has only accepted versus
   withheld outcomes, the zero-leakage guard makes a passing reviewed sample
   effectively 100% withheld; retain both metrics explicitly in the report.
5. At least **90% of sampled groups independently labelable**. Unknown labels
   are not counted as correct accepts or correct rejections. Any withheld unknown
   is potential comedy coverage loss and requires independent resolution before
   enforcement; unresolved withheld unknowns mean no-go.
6. The control has at least **ten independently confirmed comedy groups**, with
   **zero withheld**. Record any non-comedy or unknown control listings honestly;
   do not force a comedy label because of the venue.

Check these guards for both the initial sample and any supplemental reviewed
strata; a discovered coverage loss or leakage blocks enforcement even if overall
rates look favorable. Unknown accepted events remain an explicit residual risk,
subject to the labelability guard; they are not evidence of retained comedy.

Insufficient naturally occurring comedy/non-comedy groups means **no-go due to
insufficient evidence**, not a failed venue or permission to manufacture samples.
If an adapter loses event evidence, repair it and rerun the entire frozen labeled
sample before considering enforcement. Disclose such iteration as validation on
known labels rather than a new independent holdout. Do not move thresholds to
make a cohort pass. A source may remain in shadow while another qualified source
enforces. Any expansion to new sources must be bounded and separately justified;
SeatEngine results do not establish universal platform coverage.

## Required comparison and rollout evidence

For each source, retain raw-artifact hash and fetch time, event-group and
occurrence counts, sample selection, label counts, decisions by gold label,
confirmed-comedy retained/withheld denominators, confirmed-non-comedy
accepted/withheld denominators, unknown accepted/withheld counts, lineup coverage,
parent-backed counts, and stage/error counts. Preserve the pre-change source
configuration and the exact prospective policy/version used for comparison.

Model API spend is **$0**; this pilot makes no model calls. Provider request counts
and elapsed time are recorded separately; there is no provider billing estimate. No
model quality claim is made. The independent labels are an agent's evidence-based
review and have not been independently adjudicated by a human expert.

Before claiming an enforcement pass, verify the normal ingestion path retains
the sampled comedy events and reduces non-comedy writes. Approval of a policy
manifest alone is not outcome verification. Exercise scoped rollback for the
selected sources and verify candidate history and operator decisions survive.
Existing public inventory is not evidence that a new event would pass enforcement.
For a nonempty rollback audit, select one unequivocal non-comedy listing from the
frozen independent labels, record an attributed event rejection through the normal
review CLI, and verify that its immutable action survives source rollback. A
source policy/version change can make that prior action's scope stale; preserved
history is not a claim that the old approval or rejection remains active.

## Pilot results

**All three fetched sources are no-go for enforcement under the frozen guards.**
This is an observed coverage failure, not a claim that these venues do not host
comedy. No new-source enforcement default is justified by these results.

The raw provider fetch returned 50 occurrences/50 native groups for source 527,
84/37 for 595, and 216/86 for the control. All calendar objects lacked event
descriptions. Separate public event-page retrieval supplied the independent
review evidence: 147 pages, with no reported fetch errors or empty responses.
These detail pages were evidence for labeling; they were **not** secretly added
to the classifier's calendar payload.

The initial blind selection was 50/50 native groups for 527, 37/37 for 595, and
the preregistered date-stratified 60/86 for control 192. Reviewed occurrences
were respectively 50, 84, and 153. Source 527's 50 groups contain only 20 distinct
titles, reflecting recurring series with new native IDs; the control sample has
59 titles. Neither repeated series nor multiple occurrences are independent
replications. Source 595's reviewed groups have 37 distinct titles.

Independent labels were frozen at **2026-10-11 14:47:54.934257 UTC**, before this
reviewer opened classifier results. The artifact
[`task-4158-independent-labels-2026-10-11.json`](task-4158-independent-labels-2026-10-11.json)
has SHA-256
`cc86177c3446a3ac95e573ad629798feecb7dd04a5a2b103e8eda10f01199a76`.
It contains URLs, concise excerpts, confidence/rationale, occurrence IDs, and
per-source payload hashes. Calendar and fetched-page hashes are retained there;
full raw provider/page content stays in session artifacts rather than Git.

### Independent labels and prospective enforcement

The comparison artifact is
[`task-4158-reviewed-comparison.json`](task-4158-reviewed-comparison.json).
Here “withheld” includes **both rejection and uncertainty**, because either would
prevent publication in enforcement mode. A group counts as coverage loss if any
reviewed occurrence would be withheld.

| Source | Gold comedy groups | Comedy retained / withheld | Gold non-comedy withheld / total | Unknown groups, all withheld | Labelability |
| --- | ---: | --- | --- | ---: | ---: |
| 527, Santa Monica | 0 | 0 / 0; no retention estimate possible | 42 / 42 | 8 | 84.00% |
| 595, Long Beach | 14 | 2 / 12 | 17 / 17 | 6 | 83.78% |
| 192, control sample | 13 | 0 / 13 | 1 / 1 | 46 | 23.33% |

For Long Beach, confirmed comedy occurrence coverage would be **4/23 retained**
and **19/23 withheld**: seven rejections plus twelve reviews. Group coverage loss
is 12/14 (85.71%); occurrence coverage loss is 19/23 (82.61%). Non-comedy
occurrences would be 51/51 withheld. No independently labeled non-comedy group
was accepted, but that does not offset the lost comedy or resolve unknowns.

The control's confirmed comedy occurrences would be **0/28 retained** and
**28/28 withheld**: two rejections plus 26 reviews. This control deliberately used
`mixed/shadow` and an unreviewed deterministic baseline to test event-evidence
coverage. It does **not** establish that an already reviewed `comedy_only` policy
would withhold the same events; that policy's trust fallback is a different path.

Santa Monica fails the minimum confirmed-comedy sample and labelability guards,
with eight unresolved potential comedy losses. Long Beach fails confirmed-comedy
retention, labelability, and unknown-withholding guards. The control fails its
zero-comedy-loss guard. Rates describe this reviewed snapshot, not population
accuracy estimates; uncertainty labels are not errors assigned to either side.

### Stratification, parents, and coverage gaps

All available decision strata are represented in the reviewed selections.
The complete Santa Monica feed has zero accepts, 38 rejects and 12 reviews.
Long Beach has four accepts, 24 rejects and 56 reviews. The complete control
feed has zero accepts, three rejects and 213 reviews; its reviewed sample
contains all three rejects. There are no live accept examples to add for the
two zero-accept feeds, so no supplemental sample was manufactured.

All three live canonical-parent-resolved control occurrences are in the frozen
sample: That One Mailman and Sarper Guven are independently labeled comedy;
Splou remains unknown under the event-format evidence standard. All three are
reviews, demonstrating that parent rescue clears identity blocking but does not
invent affirmative event evidence. This is not a reason to undo valid parents.

No missing-lineup cases occur in these fetched calendars. Full-source observed /
partial lineup counts are 44/6 for Santa Monica, 34/50 for Long Beach, and 207/9
for the control. Missing coverage is therefore an absent live stratum, not a
synthetic case counted as live validation.

The failure is visible in concrete listings. Long Beach's UNDRGRND Comedy bills a
monthly comedy show but would be rejected. Its Beetlejuice Afterlife Cabaret and
several other burlesque-titled listings explicitly include comedy performances;
under the user's definition, they are genuine comedy coverage even though they
also include another format. Other such events would remain in review. Goodnights'
Open Mic and Ladies Laugh Lounge also have affirmative event-page evidence but
would be rejected. Familiar names and venue branding were never used to turn
the remaining biography-only control listings into confirmed comedy.

The calendar-only adapter lacks the descriptive evidence available on public
event pages. Preserving raw performer inputs alone does not close that gap.
Any adapter repair should be validated against this entire frozen sample, with
known-label iteration disclosed, before enforcement is reconsidered. The pilot
has not verified reduced **public writes** under enforcement: shadow admitted all
350 transformed occurrences, while the isolated pilot writer made zero public
writes. The comparison measures prospective withholding, not completed production
cleanup or proven retained coverage after enforcement.

### Rollback exercise handoff

An unequivocal non-comedy case selected from the frozen labels is Santa Monica
event 144263, occurrence 388738:
[Chase Walker × Danny Avila](https://santamonica.harvelles.com/shows/388738).
Its event-specific description explicitly bills live music. This supplies the
independent basis for the operator's attributed rejection and subsequent
source-scoped rollback-history check. The operator records actual application
and rollback timestamps and database verification separately; this review does
not claim those mutations occurred merely because a candidate was identified.

### Verified source rollback

After the attributed rejection of candidate 249 (Santa Monica event 144263),
the guarded rollback restored sources 192, 527 and 595 to `unreviewed/off`,
policy version 3. Read-only verification at 2026-10-11T15:00:17.376784+00:00 confirmed
all three fetch-configuration fingerprints were unchanged. Exact scoped ledger
hashes matched the pre-rollback snapshot: 350 candidates, 350 decisions,
350 observations, one human review and zero publication links. The rejection
and staged evidence remain available; rollback did not erase review history.

[The rollback verification](task-4158-rollback.json) records source states,
timestamps and before/after hashes. The original calendar-only pilot remains
**no-go**. Evidence improvements and a disclosed rerun are ongoing; no source
was promoted to enforcement by this exercise.
