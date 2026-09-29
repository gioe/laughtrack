# Public and ingestion verification

Production GET /api/v1/clubs/1347 and GET /api/v1/shows/7436372 returned HTTP200 with 650 North Avenue NE, Suite S210, Atlanta, GA30308. The club returned latitude33.7713365 and longitude-84.3667376; the show retained its ID, source link and America/New_York timezone. See verification.json for exact response fields.

After the committed migration, a separate rollback-only transaction executed the actual ClubQueries.UPSERT_CLUB_BY_SEATENGINE_VENUE SQL with stale Brooklyn address/city/state/ZIP. It preserved all nine corrected fields and the enabled source591/SeatEngine650 binding. Replaying the migration remained a no-op. The actual scheduled club-selection query still includes Whiplash. This is a controlled replay of the ingestion persistence path, not a claim that a later scheduled job was observed.

All captured foreign-key row counts and fingerprints were identical immediately before/after production application. No show, ticket, lineup, favorite, notification or click reference was detached or reassigned.

## Checks

- Production-shaped migration checks: apply, idempotence, exact rollback, rollback replay, three before-image drift cases and later-edit rollback rejection passed; all test changes rolled back.
- Actual production ingestion-upsert replay, scheduler inclusion, migration ledger and public HTTP checks passed.
- Configured web gate: 2408 passed, three savedShow.test.tsx failures (existing TASK3983). Baseline precheck ran unchanged HEAD three times: all failed, no upstream divergence, overall exit status not flaky. One baseline run additionally hit a 30-second PGlite setup-hook timeout in showTicketsSoldOutTrigger.test.ts; no task code executes in those tests. Full suite is not green. Task commits use the skill's path-limited fallback after baseline verification.

## Focused follow-ups

- TASK4113: prevent photo sourcing from replacing verified business identity; also cover unrelated candidates when identity is unknown. Correcting Atlanta city/state reduces this incident's risk but does not prove generic photo matching safe.
- TASK4114: add authoritative SeatEngine geographic evidence to the audit. Whiplash classic API lacks a structured address; its official website JSON-LD supplies it, including the conflicting ZIP that must be reported rather than blindly accepted.
- TASK4115: investigate and remove confirmed event/season labels from comedian identities. Grand Opening2353268 and Heavy Hitters2447993 remain visible in Whiplash lineups; Summer2026/518570 also owns a historical lineup. Current source labels are passed as SeatEngine talents. These are recorded for evidence-led cleanup separately from venue repair, preserving legitimate performers.

The three tasks are independent; no dependency edges were added. No Google business identity is invented: the coordinates identify the verified Ponce City Market building, and the Whiplash business place ID remains NULL pending authoritative evidence.
