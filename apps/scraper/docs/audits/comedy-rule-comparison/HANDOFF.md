# TASK-4166 handoff

This is a development comparison of an exposed public-search snapshot. It does
not authorize enforcement or stored-inventory suppression. See `README.md` and
the accompanying machine-readable results and adjudications for the measured
outcomes and their denominators.

The durable report landed in commit `265eaa4ca760`; its byte SHA-256 is
`f4e46e376c31936410a6d8361bc12b5f1603ec9d16a1047b9f608576284b8b5d`.
The 60-row adjudication artifact has byte SHA-256
`ee674e0cd6d7cf48ba5f3d6577dedd1adc41cbd67cf192d28a811bb7833374fc`.
Tusk risk context **861** on TASK-4160 and **862** on TASK-4159 preserve this
handoff in their compiled task briefs. Neither task's validation or application
criteria were marked complete by this report.

## Frozen candidate

- Baseline: `a0f28e84f32edca40e8f3e09d6158e4545a2489b` (before TASK-4163).
- After TASK-4163: `4988d1e4a90abeb2ff13a215b787fc9ab76c605c`.
- After TASK-4164: `df90d01eeec5d8b67ae214c02adfc69692c6d3fb`.
- Candidate: `346cac72604a6338673fff90f5e3d6781de49b13` (after TASK-4165).
- Classifier: `comedy-eligibility-v2-rules-v3`.
- Rule versions: `comedy-event-rules-v1`, `comedy-context-rules-v1`,
  `comedy-audience-formats-v1`; audience policy `comedy-audience-policy-v1`.
- Corpus: `comedy-search-2026-10-11-v1`; manifest SHA-256
  `f6e6e5f11c069e81cb4331cb3884df3b9ceb47ce275db23722c92365a4936c28`.

The title-only diagnostic uses an explicit unreviewed/off policy and no raw
performer observations. That is an experimental configuration, not a historical
source-policy snapshot. All 2,886 public occurrences lack resolved ingestion
source ownership and the required prefilter identity/policy evidence. Do not
convert diagnostic rejections into an executable suppression batch.

## TASK-4160: fresh validation and bounded enforcement

Bring the final candidate into the retained TASK-4160 worktree before collecting
predictions. Freeze the exact code revision, source policies, raw inputs and
canonical/deny snapshots. Policy/version changes invalidate prior scoped reviews;
preserved review history does not make an old approval current.

Exclude this entire exposed search corpus and all previously prediction-exposed
TASK-4158/TASK-4160 native groups from the fresh holdout. The search archive has no
resolved source-native group mapping, so it cannot itself supply a reliable
native-ID exclusion list: reconcile captured source/native identities and title,
venue and series evidence conservatively before declaring a new group fresh.
Repeated occurrences or repeated scrapes are not new independent groups. Freeze
labels before revealing classifier outcomes. Keep supplemental strata separate.

Preserve the preregistered guards in
[`task-4158-rollout.md`](../task-4158-rollout.md): each mixed source needs at least
five confirmed comedy and ten confirmed non-comedy groups; no confirmed comedy
may be withheld, no confirmed non-comedy accepted, at least 90% of non-comedy
withheld and at least 90% labelability. Unresolved withheld unknowns mean no-go.
The control requires at least ten confirmed comedy groups and no comedy losses.
Report both occurrence and native-group denominators. Development accuracy does
not satisfy these requirements, and insufficient data does not justify lowering
the thresholds.

Distinguish genre from audience format. A comedy class or comedy film is not
evidence that comedy never occurs; excluding it is a product-format policy
choice. Format-policy exclusions of confirmed comedy must remain visible as
coverage losses under the original comedy-retention guard, unless a separately
authorized scope change revises that guard before validation. Preserve genuine
live graduation/showcase events and mixed bills that contain comedy.

Enable only source cohorts that pass, verify actual ingestion coverage, and
exercise source-scoped rollback with prior configuration and affected counts.
Keep candidate and review history intact. Mixed Harvelle's feeds require event
evidence; venue branding and comedian DB membership do not confer source trust.
Blocked-only lineups require valid parent resolution or documented scoped
structural/event review. OpenAI remains optional, with no provider calls required
by this comparison.

## TASK-4159: reversible stored-inventory cleanup

Keep the TASK-4160 dependency. After validation, obtain current source ownership,
raw event evidence and identity/policy versions for each proposed batch. Produce
a read-only retain/review/suppress manifest, then apply only reviewed, versioned
dispositions with idempotency and audit history. Unknowns remain reviewable.
Preserve venue directory membership, valid parent-backed lineups and historical
references. Broad identity repair remains TASK-3982.

Verify suppression across discovery/search/API and future promotions, and ensure
re-scraping cannot silently republish suppressed shows. Record actual affected
counts and test restoration of prior visibility. A later live-search comparison
must distinguish newly prevented ingestion from this cleanup and from ordinary
inventory/date changes. Neither this offline report nor prospective filtering
alone removes existing public shows. No production state changed in TASK-4166.
