# TASK-4160 rule remediation

The corrected title-only diagnostic restores **12 previously withheld live-comedy
occurrences**, retains all six supported non-comedy rejections, and introduces
no new rejection or loss of a previously accepted occurrence. Six bingo listings
move from reject to review; two remain known comedy coverage losses. This is
development evidence, not authorization to enable filtering.

## Reproducible comparison

- Previous candidate: `346cac72604a6338673fff90f5e3d6781de49b13`.
- Corrected candidate: `99cc4161b0d15a76da4d28da158fcbe6007bc5e9`.
- Classifier: `comedy-eligibility-v3-rules-v4`; context rules
  `comedy-context-rules-v2`; audience rules `comedy-audience-formats-v2`.
- Availability/activity rules and audience policy retain their v1 identifiers.
- Frozen corpus: `comedy-search-2026-10-11-v1`, 2,886 occurrences,
  2,175 exact venue/title groups, zero resolved source/native groups.
- Manifest SHA-256:
  `f6e6e5f11c069e81cb4331cb3884df3b9ceb47ce275db23722c92365a4936c28`.
- [Full comparison](task-4160-rule-remediation.json), SHA-256:
  `b6b18219d74c459abf142a0773b9571a50cfe378744640377f9b1f166b5a4328`.

From `apps/scraper`, with full local Git history and a new output path:

```sh
PYTHONPATH=src:. .venv/bin/python3 scripts/core/report_comedy_rule_remediation.py \
  --candidate 99cc4161b0d15a76da4d28da158fcbe6007bc5e9 \
  --output /private/tmp/task-4160-remediation-rerun.json
```

The tool checks the original TASK-4166 artifact hashes, reproduces its candidate
decisions, and runs both committed revisions in isolated subprocesses with
identical inputs. All original corpus, labels and TASK-4166 report bytes are
unchanged. Database, network and model calls are forbidden in replay.

## Paired results

| Outcome | Previous | Corrected |
| --- | ---: | ---: |
| Accept | 332 | 344 |
| Review | 2,507 | 2,501 |
| Reject | 47 | 41 |

There are exactly 18 changed decisions: 12 review → accept and six reject →
review. The 332 previous accepts remain accepted. No new rejection occurs.
The full report preserves old/new decisions, rule evidence, titles, venue context
and historical evidence references for every changed occurrence.

| Historical TASK-4166 review cohort | Occurrences | Corrected accept / review / reject |
| --- | ---: | ---: |
| Live comedy previously withheld | 14 | 12 / 2 / 0 |
| Supported non-comedy | 6 | 0 / 0 / 6 |
| Non-public promotion or closure | 4 | 0 / 0 / 4 |
| Non-audience mixer | 1 | 0 / 0 / 1 |
| Comedy classes/film/workshop | 9 | 0 / 1 / 8 |
| Unresolved genre | 26 | 0 / 4 / 22 |

These are the 60 historical, post-outcome judgments. They are neither a new blind
sample nor representative of the entire inventory. The original 54 frozen
comedy labels still have only ten accepts and 44 withheld outcomes: the 12
restored titles were identified as comedy in the supplemental review, while their
original labels remain unchanged. Keep these two label sets separate.

## Review of every changed decision

The [separate outcome review](task-4160-rule-remediation-review.json) records a
post-outcome agent review of all 18 changes against this exact report digest and
candidate. The machine report intentionally retains its generated `pending`
status; the separate review does not rewrite historical artifacts or claim an
independent evaluation.

| Public show IDs | Billing reviewed | Result |
| --- | --- | --- |
| 8013080 | Laughter at the Bit: Stand-up Comedy Open Mic | Accept |
| 6445698 | Live at Sunset Strip: Comedy Showcase | Accept |
| 7612243 | Stand up comedy on the historic “Comedy Row” | Accept |
| 3214767 | Don’t Be Yourself! — Weekly Character Comedy Open Mic | Accept |
| 6085247, 6619318 | Live at the Barbershop NYC: Stand Up Comedy Show | Accept |
| 7852401 | Laughs at the Library Comedy Show | Accept |
| 7978575, 7978576 | THE UPSTAIRS COMEDY SHOWCASE | Accept |
| 6028959 | Live at the Barbershop Houston: Stand Up Comedy | Accept |
| 7243042 | Sunset Strip After Dark Comedy Showcase | Accept |
| 7679999 | “Make 'Em Laugh” Comedy Night | Accept |
| 7367674, 6720036 | Uptown Adult Bingo; Summer Orlando's Drag Bingo | Review; known comedy still withheld |
| 5144686, 3679014, 4562223, 3621437 | R&B Bingo and three drag-bingo listings | Review; genre unresolved |

The title repair preserves explicit performance billing after a location or
separately delimited show name. Quoted offerings, cancellation/negation,
biographical credits and unrelated venues/times remain guarded. Both context and
audience extraction share the repair, avoiding a residual ambiguous-format hold.

Bingo alone no longer establishes non-comedy. Explicit bingo-plus-comedy billing
can still support comedy; independently billed concerts or sports remain negative
evidence. A bingo review is not an acceptance. The two known mixed-comedy bingo
events originate from Eventbrite and the Comix scraper, so their archived public
descriptions cannot be relabeled as validated SeatEngine collector evidence.
They need source-bound detail or scoped event review before retention can pass.

The retained TASK-4160 collector work is reconciled with the newer rule families:
description and biography panels retain separate authority and citations. Only
the validated description panel feeds the shared format rules. Instructions in
either panel invalidate the combined marker. Blocked-only identities and valid
parent resolution retain their existing rules; these changes grant no identity
exception or source-wide trust.

## Verification and remaining gate

The pre-fix regression failed on the expected Laughter at the Bit hold. All 130
focused rule/collector/gate checks passed after correction, and the full scraper
commit gate passed in 91.7 seconds. Seven remediation-report tests passed,
including historical reproduction, cohort losses, artifact integrity and output
protection. Pyflakes and whitespace checks passed.

Strict ingestion replay still supports **zero of 2,886 occurrences** because
source ownership and prefilter identity/policy/raw-event snapshots are missing.
Public descriptions and public lineups are not substituted for that evidence.
This title diagnostic measures neither real publication nor population accuracy.
Comedy classes/films remain comedy content even when format policy withholds them.

The [fresh collection recheck](task-4160-validation.md#subsequent-fresh-collection-check)
found 348 occurrences / 171 native groups and zero new groups. Fresh labels,
source-level validation, scoped enforcement and rollback remain outstanding under
criteria 13560/13561. Exclude the entire exposed search corpus as well as prior
native groups before selecting the next holdout. TASK-4159 remains dependent on
that validation. This remediation changed no production policies, public records,
identity data or model configuration.
