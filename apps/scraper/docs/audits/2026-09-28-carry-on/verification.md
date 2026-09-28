# Applied repair and verification — TASK-4066

Migration 20260928150000_correct_carry_on_identity was the only pending Prisma migration and applied successfully on 2026-09-28 at 15:36 UTC using the locally pinned Prisma binary. It changed exactly club 600 and source 336, and inserted one venue denial for the verified Phoenix Carry On place. Original field images are retained inside task_4066_disposition; before.json is the independent snapshot.

The public club endpoint https://www.laugh-track.com/api/v1/clubs/600 returned HTTP 200 with the corrected Phoenix address, ZIP 85004 and coordinates. The public show endpoint /api/v1/shows/6995541 returned HTTP 404, Show not found. The club remains an active business but is hidden from discovery. This is not a cancellation assertion.

## Preservation

All 713 shows (including 38 upcoming reservations), 1,788 tickets, 1,566 show tags and 136 scraper-run references have unchanged counts and complete-row hashes. Other club/show foreign-key associations remain unchanged. Purchase-click counts grew naturally by four during the investigation, from 4,308 to 4,312 venue-linked records and 4,276 to 4,280 show-linked records. Filtering the after-state by the original snapshot timestamp reproduces both original click hashes exactly: no original references were removed or rewritten. No private click payloads are retained in these artifacts.

## Recurrence and rollback

The actual ClubQueries.UPSERT_CLUB_BY_SEATENGINE_VENUE was replayed in a later transaction with the former New Rochelle metadata. It preserved the corrected Phoenix identity, hidden visibility and disabled source. The transaction was rolled back. The real GET_ALL_CLUBS scheduling query excludes club 600. The verified Google place denial protects discovery. No additional prevention code change is required for these existing paths; no live scraper was forced to ingest excluded inventory.

Before applying, rollback-only production-shaped validation checked original-source drift rejection, application from a non-UTC session, repeat application, actual national upsert, guarded rollback rejection after an intervening edit, and rollback/replay. The source timestamp trigger exposed one issue during testing: updated_at refreshes on every UPDATE. Final guards therefore compare business fields rather than rejecting harmless timestamp refreshes. Original timestamps remain recorded; rollback intentionally refreshes that audit timestamp.

rollback.sql is an operator-only recovery artifact, not an automatic migration. It restores the known-bad original identity and visibility, so use only for deliberate rollback. It rejects intervening business-field changes and removes only the task-owned Phoenix denial. After a rollback, a separately reviewed forward migration is needed to reapply through Prisma; do not edit the applied migration or its checksum.

Existing focused tests passed: two SeatEngine disposition-upsert tests and 22 findShowById tests including hidden-club cases. The full web suite had 2,408 passing tests and three failures in savedShow.test.tsx. All three failures reproduced on three unchanged HEAD runs (not flaky; no origin divergence), already tracked by TASK-3983. These unrelated failures were not changed.

Evidence: after.json, migration-validation.json and verification.json. The validation uses frozen evidence plus explicitly documented live checks; it does not predict future source programming. Reassess the exclusion if Carry On starts genuine comedy programming.
