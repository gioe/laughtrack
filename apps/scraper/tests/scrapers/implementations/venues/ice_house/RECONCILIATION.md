# TASK-4103 — Que Sera promotion reconciliation

Verified 2026-10-05 using HttpClient.fetch_json with curl-cffi AsyncSession,
against the configured queseralb Tockify ngevent endpoint. The first 200-event
page contained 37 After Comedy Happy Hour occurrences and 37 Bear City Comedy
occurrences. These are page counts, not full-calendar inventory totals.

The retained matched-representatives fixture and current source agree:
calendar 6644435d5968360cdd7c9a18, promotion uid315, performance uid11.
Promotion text advertises Hamms at 3 dollars and Fernet/well drinks at 5 dollars
after Bear City Comedy. Bear City advertises touring comedians and has no
ticket button or admission price. The pre-fix extractor admitted both records.

Production source5914 belongs to club8856. Its existing comedy_filter remains
enabled; exclude_title_patterns now includes the anchored promotion title.
The scraper applies these configured exclusions after pagination and before
ticket enrichment. Deployment of the new scraper is required for enforcement;
older running code does not consume this metadata key.

The migration uses the exact 78 retained show/ticket IDs, dates and URLs from
the September27 matched-ids cohort. It checks source identity and each surviving
show identity, rejects unexpected tickets or prices, and aborts if saved shows,
notifications, lineups or discovery feature snapshots appear. It never reads
drink amounts as admission. Other promotion rows are not cleanup targets.

Before cleanup: 78 cohort shows, 78 unknown-price tickets, 104 tag links,
zero saved shows/notifications/lineups/discovery snapshots. Initial inspection
found 761 click records; 763 existed when the transaction executed. The
transaction locked and snapshotted those clicks and asserted all 763 records
and every attribution field survived unchanged except show_id, which becomes
NULL through the existing ON DELETE SET NULL foreign key. No user identifiers
or click payloads are retained in the audit file.

Validated against production data in a rolled-back transaction first. Applied
only this migration SQL in a committed transaction on 2026-10-05; no unrelated
pending migrations were deployed. A second rolled-back execution removed zero
rows, confirming safe replay by Prisma deployment. The migration ledger is
left to the normal Prisma deploy process.

After cleanup: zero cohort shows/tickets/tag links; all 763 clicks preserved.
Club promotion rows fell from93 to15 (14 past,1 future outside the fixed cohort).
All93 Bear City rows and all93 unknown-price tickets remain, including78 future
performances. One unrelated past Lashoyosfunkies Presents row remains.
Club total_shows was refreshed. The accompanying reconciliation_before.json
retains deleted show/ticket/tag data for recovery; it is not a current inventory
target. A normal clean scrape can reconcile the single extra future promotion
after the filter deploys; this task does not broaden the fixed-cohort deletion.
