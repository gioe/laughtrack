# Production verification — TASK-4046

Seven exact address-verified coordinate pairs were applied on September 24, 2026, after a rollback trial. Guards required unchanged venue ID/name/address/city/state/country/postal code, visible active physical-venue status, and both coordinates still NULL. No other venue coordinates or show timestamps changed. cached-repair-rollback.json and cached-repair-apply.json record the same seven IDs and timestamp fingerprint.

| Venue | ID | Upcoming shows |
| --- | ---: | ---: |
| Fallout Theater | 15972 | 140 |
| Loony Bin Wichita | 16111 | 130 |
| Greenwich Village Comedy Club | 17080 | 103 |
| Olsen Run Comedy Club | 16133 | 95 |
| Dallas Comedy Club | 16112 | 94 |
| Loony Bin Little Rock | 16109 | 82 |
| Walnut Street Theatre | 22513 | 74 |
| Total | | 718 |

The independent final snapshot contains 783 visible venues still missing coordinates, including 679 with 2,761 upcoming shows. remaining.json records every unresolved address; these are not assumed unresolvable forever. Two festival records remain outside the physical-venue queue. Among eligible physical rows still missing coordinates, 775 have no attempt under the new tracking and six have one recorded unresolved attempt.

## Actual bounded runs

After applying the schema, the updated shared production code ran twice with limit=3. The first batch selected 11485,11665,11709 and recorded three unresolved outcomes. The second selected different venues 11754,11757,11766 and recorded three unresolved outcomes. Neither run overwrote a coordinate. The first batch therefore demonstrably did not monopolize the second. See production-batches.json.

Measured new tracking across the seven cached verified repairs and six live batch evaluations: 13 attempted venues, seven resolved, six unresolved, zero provider failures, zero retries, zero skipped writes. Historical attempts predating these fields remain unknown. Cached probe rejections that were not processed by the production queue are preserved in the evidence files, not mislabeled as persisted attempts.

All 24 controlled comparison requests returned HTTP 200. Nine deduplicated queries returned candidates, but five of the twelve venues remained unaccepted: High Line had two distinct matching positions; Rumor's, Tulsa Loony Bin and Quezada's returned no candidate; St. Louis Funny Bone did not satisfy exact locality matching. Canadian addresses with missing country evidence, suite/level addresses, aliases and source metadata gaps can remain unresolved under the deliberately conservative matcher. The queue will progress through other venues while such rows cool down; do not weaken identity checks merely to reduce the count.

## Verification and rollout

The schema migration was applied directly and is idempotent for later Prisma deployment. Tests cover sequential runs, country/city/postal conflicts, malformed coordinates, existing partial pairs, concurrent changes, provider block/backoff, cross-run pacing, database failure reporting, and CLI preview safety. A local PostgreSQL harness exercises the actual query and update statements plus cross-connection advisory locking. Full scraper gates and Prisma validation passed.

Production runs above used this worktree's updated code directly against the production database; they do not claim the next scheduled hosted job has already executed. Nightly ingestion picks up the merged code. At the default limit of 30, strict 15-second pacing can take roughly 7.5 minutes. The manual CLI defaults to SELECT-only preview; use --apply only for an intentional bounded run. TASK-4076 tracks retained nightly outcome artifacts; per-venue attempt state is already durable.

Source coordinates: © OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright). See DIAGNOSIS.md and provider evidence for query provenance and policy.
