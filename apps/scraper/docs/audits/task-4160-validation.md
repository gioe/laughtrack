# TASK-4160 fresh validation preregistration

**No-go: no fresh event groups are available in this inventory.** This records a
sampling result, not successful independent validation. Criterion 13560 remains
incomplete. No new labels were fabricated and TASK-4158 gold labels remain frozen.

The selection and thresholds were frozen at **2026-10-11 16:16:36.527709 UTC**,
before this reviewer accessed any TASK-4160 classifier outcomes. The reviewer has
seen TASK-4158 outcomes; those exposures are explicitly excluded below.

## Frozen inventory and exclusions

The fresh provider inventory was collected at 2026-10-11 16:15:01.933932 UTC.
Comparison uses `(source_id, native event.id)`, not occurrence IDs or scrape runs.

| Source | Fresh fetch occurrences / groups | Previously gold-reviewed groups | Previously exposed but unlabelled groups | Strict fresh groups selected |
| --- | ---: | ---: | ---: | ---: |
| 527 — Harvelle's Santa Monica | 50 / 50 | 50 | 0 | 0 |
| 595 — Harvelle's Long Beach | 84 / 37 | 37 | 0 | 0 |
| 192 — Goodnights | 216 / 86 | 60 | 26 | 0 |
| Total | 350 / 173 | 147 | 26 | 0 |

All 173 groups were present in the prior pilot's exposed population. The 26
Goodnights groups outside its gold sample are not an untouched holdout: their
prior outcomes were available. New performances of an old native event also do
not create fresh groups. A source is not disqualified as a comedy venue because
its current feed cannot supply a fresh validation sample.

The immutable selection manifest is
[`task-4160-fresh-selection.json`](task-4160-fresh-selection.json), SHA-256
`c4a1aac80047666b7666baaad812ef85fbf51d89be605d9e8334c9c4d796099e`.
It enumerates all excluded pairs and the empty selection. Its component hashes
use UTF-8 JSON, sorted keys and compact separators; exclusions are sorted by
source ID then integer event ID:

- Fresh inventory SHA-256: `11f691555303ab396acb4b10d3aaeaec2d912fbd5f592007bf650de1d1919089`.
- Prior inventory SHA-256: `237c6372890bb473328491eae97a3b50f63110accc7bd4cc3bdf4c83152dbedc`.
- Frozen prior labels SHA-256: `cc86177c3446a3ac95e573ad629798feecb7dd04a5a2b103e8eda10f01199a76`.
- Excluded pair list SHA-256: `00db33e329ff7adf6e46699bce7bb3c3d6bc61419d711ad217f1440911af9bcc`.
- Empty selection SHA-256: `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.

Full raw provider content stays in private session artifacts. The hashes identify
specific frozen inputs, not a promise that later fetches or this living report
have identical bytes.

## Unchanged operational thresholds

Retain the [TASK-4158 preregistration](task-4158-rollout.md). Each mixed source
must independently have at least five confirmed comedy groups, zero confirmed
comedy groups withheld, at least ten confirmed non-comedy groups, at least 90%
of confirmed non-comedy groups withheld, and zero accepted confirmed non-comedy
groups. Zero accepted non-comedy makes the observed withholding requirement
effectively 100%; report both metrics rather than silently weakening either.

At least 90% of sampled groups must be independently labelable. Any unresolved
withheld unknown means no-go. Unknown accepts remain an explicit residual risk,
not evidence of retained comedy. Goodnights must have at least ten independently
confirmed comedy groups with zero withheld. Report its non-comedy and unknown
listings honestly and apply the leakage and uncertainty safeguards; do not
invent ten non-comedy control groups or label venue branding as comedy evidence.

Both `reject` and `review` withhold publication. A comedy group fails retention
if any of its evaluated occurrences is withheld or lost during transformation.
Report group and occurrence denominators separately. These small operational
samples do not establish a statistical accuracy guarantee. Goodnights source
trust review and old-miss adjudication are separate work; neither supplies fresh
holdout observations nor compensates for a mixed source's failed guards.

## Procedure when fresh groups arrive

1. Freeze the candidate code revision and explicit prospective source policies
   before comparison. Collect source inventories through the actual SeatEngine
   client, without classification, public writes or model calls. Retain fetch
   times, request counts, errors, elapsed time and raw hashes.
2. Exclude every previously exposed native group, beginning with this manifest.
   Maintain an append-only exposure ledger for subsequent batches. New native
   IDs for recurring titles are flagged as correlated series, not independent
   replications. Record excluded and eligible counts before sample selection.
3. Census a source with at most 60 eligible groups. Otherwise sort by earliest
   upcoming occurrence and native ID, split into three date-ordered thirds,
   and take 20 evenly spaced groups per third. Freeze selected IDs and raw
   hashes before labeling. Do not select only listings that appear likely to
   satisfy comedy or non-comedy minimums.
4. Give the reviewer event-specific pages, title, raw performers, dates and
   provenance URLs. Withhold predictions, resolved block state and suggested
   labels. Confirm actual live comedy billing, including comedy within mixed
   performances; musician biographies, venue names and database membership
   alone are insufficient. Freeze `comedy`, `non_comedy` or `unknown` labels,
   concise supporting evidence, reviewer identity, time and artifact hash.
5. Only then compare every selected occurrence under the frozen prospective
   policy. Count upstream filtering and failed transformations as coverage
   losses rather than omitting them. Report decision-by-gold tables, unknowns,
   lineup coverage, parent and structural exceptions, all sample denominators
   and per-source go/no-go reasons. Reusing labels after implementation changes
   is development-set validation and requires disclosure and a subsequent fresh
   sample before an independent validation claim.
6. If a decision/exception stratum is absent, the operator may select up to ten
   additional unexposed groups deterministically for blind review, following
   TASK-4158. Freeze their labels before comparison and report them separately;
   enriched strata are not a prevalence sample. Missing naturally occurring
   cases remain absent. Insufficient sample minima remain no-go.

The updated `scripts/core/pilot_comedy_eligibility.py` reports the unreviewed
baseline separately from effective decisions under the configured source policy.
Its `--prospective-manifest` option evaluates an explicitly proposed policy
without applying that policy. Existing human reviews are loaded against the exact
source, event key, payload fingerprint, identity fingerprint and policy version;
the report exposes stale status, review version and action ID rather than
fabricating approvals for the proposal. This helper invokes no production show
writer. Its optional shadow staging records candidate observations only. These
outputs support a policy comparison but do not themselves establish retained
publication or a safe universal new-source default. They do not supply the
missing fresh labels or complete criterion 13560.

Model API spend is $0; no model calls were made. Inspection of the executed
collector `/private/tmp/task4160_fresh.py` confirms three logical
`SeatEngineClient.fetch_json` calendar calls, one per source, with no detail-page
or venue-request fanout. Transport retries/network attempts and precise elapsed
time were not instrumented and remain unavailable, not zero. The frozen raw
artifact records the fetch start timestamp only. No provider billing estimate is
asserted here. No source enforcement or configuration change is authorized by
this empty selection. No-go sources remain off or shadow.

## Known-label development replay

A successful read-only CLI replay at **2026-10-11 16:23:00.290443 UTC** used the
previously exposed, description-enriched TASK-4158 input and current database
identity/review snapshots. This is development-set reuse, not fresh independent
validation. The private output `/private/tmp/task4160-development-effective.json`
has SHA-256 `d078fc978527a1b6c42082a0b186e049121530fc927492046cf8afedd3c44ce6`.

| Source | Occurrences transformed | Baseline accept / reject / review | Effective accept / reject / review |
| --- | ---: | ---: | ---: |
| 192 — Goodnights | 216 | 0 / 2 / 214 | 0 / 2 / 214 |
| 527 — Harvelle's Santa Monica | 50 | 0 / 39 / 11 | 0 / 38 / 12 |
| 595 — Harvelle's Long Beach | 84 | 8 / 36 / 40 | 8 / 36 / 40 |

All 350 occurrences transformed, with zero upstream-filter or conversion losses.
Santa Monica's single changed outcome reflects a preserved version-2 human
review whose scope is stale under source policy version 3; the effective result
is a review hold, not a renewed rejection or a silently reused approval. The
other sources' baseline and effective counts agree.

These are **eligibility-only decisions**. All three sources were configured
`unreviewed/off/version 3`; off mode bypasses screening in ordinary publication.
The CLI invoked no public writer, performed no shadow staging and made zero
model calls. These counts establish neither current public suppression nor an
enforcement pass. The strict fresh selection remains empty and criterion 13560
remains incomplete.
