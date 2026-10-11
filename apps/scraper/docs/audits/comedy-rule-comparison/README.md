# Frozen ingestion-rule comparison — TASK-4166

**The new rules are not ready for enforcement on this evidence.** The title-only
diagnostic identifies useful exclusions, but also rejects two reviewed live-comedy
bingo events and newly holds twelve other explicitly billed live-comedy listings.
Full ingestion replay is unsupported for every archived occurrence because the
public snapshot lacks source ownership and raw ingestion evidence.

No database, source policy, public show, venue visibility or model provider was
changed. This report does not demonstrate a reduction in the live search API.

## What was compared

The immutable
[`baseline-v1` archive](../comedy-search-rules/baseline-v1/README.md) contains
2,886 published occurrences, 2,175 exact venue/title groups and 702 venues for
October 11–17, 2026. Its original triage flags are hypotheses, not truth labels.
The frozen agent review labels 54 occurrences comedy, 14 non-comedy and 170
reviewed-unknown; another 2,648 were unreviewed. These deliberately selected
labels cannot estimate the false-positive rate of all clubs or all shows.

[`comparison.json`](comparison.json) records exact commit, imported-source,
policy, input and corpus hashes. The same inputs run through each revision's
actual `capture_event_inputs`, `event_evidence` and pure
`classify_comedy_eligibility` functions in an isolated process. This compares
deterministic eligibility only; the publication writer, human-review overrides
and optional model path are not invoked. Network/database connections are
blocked. The runner verifies imported project files come from the frozen
revision, avoiding the shared virtualenv's editable primary-checkout imports.

The full replay reports **0 supported / 2,886 unsupported** occurrences. Every
row lacks resolved publication-linked source ownership, prefilter performers,
identity snapshots and source-policy/raw-event snapshots. Only 67 occurrences
have a stored native performance ID; none has a resolved source-native group.
Thus the native-group denominator is **0 resolved**, not 2,175. Exact venue/title
groups and recorded scraper keys are explicitly labeled diagnostic proxies.
Missing inputs are never counted as successful removals.

The separate title-only diagnostic supplies only the archived title, an explicit
unreviewed/off/version-1 experimental policy, and empty/missing raw performer
observations. Public descriptions are used for adjudication, but are not
fabricated into collector-validated ingestion evidence. Public lineups omit
blocked identities and cannot reconstruct the user's blocked-only/valid-parent
distinction. The historical baseline is the baseline **code** on these restricted
inputs; the original API state is separately `observed_publication`, not proof
that an earlier classifier accepted these shows. Off mode itself does not enforce
the eligibility decisions tabulated below.

## Title-only results

| Revision | Accept | Review | Reject |
| --- | ---: | ---: | ---: |
| Before TASK-4163, `a0f28e84f` | 308 | 2,578 | 0 |
| After TASK-4163, `4988d1e4a` | 308 | 2,571 | 7 |
| After TASK-4164, `df90d01ee` | 305 | 2,544 | 37 |
| After TASK-4165, `346cac726` | 332 | 2,507 | 47 |

Across the combined change, 42 reviews become accepts, while 18 accepts become
withheld: five rejects and thirteen reviews. The net increase of 24 accepts
conceals those losses. Another 42 reviews become rejects; those events were
already withheld by the restricted baseline, so they are not newly prevented
publication. A total of 102 occurrence decisions change.

The machine-readable report includes sequential incremental transitions,
individual rule-hit effects and overlap deduplication. Candidate evidence
ablations are diagnostics within the candidate classifier, not substitutes for
the historical code comparison: the tasks also changed legacy title matching.
Do not sum overlapping rule hits as separate removed shows.

TASK-4163 adds seven rejects. TASK-4164 adds 30 rejects, gains nine accepts and
holds twelve prior accepts. TASK-4165 adds ten rejects (five from accepts), gains
33 accepts and holds one additional prior accept for review. These are paired
changes from the immediately preceding code revision, not independent rule totals.
The candidate has 784 individual rule matches on only 433 unique occurrences;
197 occurrences match multiple rules. Music plus karaoke, for example, can
describe one event rather than two removals.

Candidate audience formats are independently reported: 201 live performance,
7 instruction, 2 screening, 1 mixer, 2 mixed, 26 ambiguous and 2,647 unknown.
Older revisions did not emit this field; their format is not recorded, rather
than retrospectively inferred. Format does not determine whether comedy occurs.

| Frozen reference genre | Baseline accepted / withheld | Candidate accepted / withheld |
| --- | ---: | ---: |
| Comedy, 54 occurrences | 8 / 46 | 10 / 44 |
| Non-comedy, 14 occurrences | 0 / 14 | 0 / 14 |
| Unknown or unreviewed, 2,818 occurrences | 300 / 2,518 | 322 / 2,496 |

Candidate withholding includes both reviews and rejects: for frozen comedy,
34 reviews and 10 rejects; for non-comedy, eight reviews and six rejects; for
unknown/unreviewed, 2,465 reviews and 31 rejects. Most holds reflect missing
title evidence, not newly discovered false positives. The 54 reviewed comedy
occurrences are a selected development denominator, not corpus recall. Unknown
accepts are not demonstrated retained comedy and unknown rejections are not
demonstrated non-comedy removals.

## Adjudication of all proposed exclusions

[`adjudications.json`](adjudications.json) records a post-outcome review by
`codex:/root`, not a human or blind evaluator. Every one of the 47 candidate
rejects and every baseline-accept → candidate-review transition is covered:
**60 occurrences / 50 exact venue-title-description groups**. Generic
missing-evidence reviews are reported as holds, not proposed successful
exclusions. Each adjudication preserves the original reference label and adds
separate evidence, judgment and rationale; frozen labels remain unchanged.
Every occurrence was checked against its own archived title/description.

| Adjudication | Occurrences | Interpretation |
| --- | ---: | --- |
| Supported non-comedy programme | 6 | Karaoke, music open mic, EP-release concert and mechanical bull rides |
| Supported non-public listing | 4 | Party-booking promotions and private-event closures; genre unknown |
| Supported non-audience format | 1 | Corporate networking mixer; genre unknown |
| Comedy format withheld | 9 | Eight training listings and one comedy-film screening; not non-comedy findings |
| Live comedy withheld | 14 | Two rejected mixed-comedy bingo events and twelve newly held live-comedy listings |
| Unresolved | 26 | Sparse descriptions, mixed bills or activities with an unverified comedy component |

These judgments describe the preserved advertised programme, not proof that no
unadvertised comedy ever occurs in person. Only six of the 60 have supported
non-comedy labels. It would be misleading to call all 47 rejects false positives
removed, or turn the post-outcome development judgments into independent accuracy.

Concrete findings to resolve before rollout:

1. **Location text erases affirmative billing.** Splitting every title at `at`
   drops the comedy offering in “Laughter at the Bit: Stand-up Comedy Open Mic,”
   “Live at Sunset Strip: Comedy Showcase,” the Barbershop listings and “Laughs
   at the Library Comedy Show.” Preserve event billing while excluding venue-only
   branding; merely removing the guard would reintroduce the original risk.
2. **Global uncertainty words reject legitimate show names.** Quoted titles,
   “Don't Be Yourself,” “The Upstairs Comedy Showcase” and “After Dark Comedy
   Showcase” become invalid or ambiguous despite explicit comedy billing. Scope
   quotation, negation and other-room guards to what they actually qualify.
3. **Title-only negative formats lose mixed comedy.** Uptown's Adult Bingo and
   Comix's Summer Orlando Drag Bingo have reviewed same-event comedy evidence
   in their archived descriptions. Detail collection and conflict review are
   necessary before treating the title's bingo match as a safe rejection.
4. **Unknowns cannot become wins by assumption.** Walking tours, drag bingo,
   trivia, a mixed karaoke/open-mic and the John Cusack appearance/screening need
   event-specific evidence before a safe exclusion can be adjudicated.
5. **Keep format policy explicit.** Comedy instruction and comedy films may be
   outside the intended audience-show product, but they are not examples of
   venues where comedy never occurs. Format loss must not inflate non-comedy
   precision or disappear from the current comedy-retention guard.

## Handoff and reproducibility

[`HANDOFF.md`](HANDOFF.md) pins full revisions and the corpus hash, and gives
TASK-4160 and TASK-4159 the validation, exposure-exclusion and rollback steps.
These findings must be addressed or explicitly bounded before fresh validation.
Any fixes require a new frozen candidate and a disclosed development rerun.
This exposed archive cannot satisfy TASK-4160's fresh independent-label guard.
Do not enable enforcement or suppress existing inventory from this report.

Run the comparison from `apps/scraper` with the project virtualenv and the
committed revisions available locally, choosing a new output file:

```bash
PYTHONPATH=src:. .venv/bin/python3 scripts/core/compare_comedy_event_rules.py \
  --output /private/tmp/comedy-comparison-rerun.json \
  --adjudications docs/audits/comedy-rule-comparison/adjudications.json
```

The CLI refuses both existing output files and output paths within the frozen corpus.
Synthetic strict inputs assert snapshot completeness; their digests establish
input consistency, not independent proof that a caller captured every identity.
Tests exercise immutable replay, missing-evidence handling,
metrics, evidence completeness and the read-only boundary. No provider API key
is needed.
