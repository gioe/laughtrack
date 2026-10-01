# TASK-4081: Annoyance performance identity

## Verified source and repair scope

On September 30, 2026, all 12 configured ThunderTix calendar windows were fetched through the scraper HTTP stack. The first request profile encountered HTTP 403 and browser fallback could not parse a calendar. Retrying with Chrome 124 impersonation, JSON Accept, and the merchant Referer succeeded. The public identity/time/URL extract is in `source-evidence.json`; challenge responses were not treated as evidence of cancelled performances.

The calendar contains 306 unique raw performances and 275 after the configured CLASS:/TRAINING CENTER: exclusions and public-availability filter. At capture, 262 are future performances. There are 38 same-time pairs (76 performances), without verified room names. Distinct native event/performance IDs establish separate source records; no room names are invented.

Before repair, production had 724 Annoyance show rows and 724 tickets. All 199 currently future rows have ticket performance IDs present in the complete source inventory. No future row is approved for retirement. The reviewed plan assigns identities to 210 existing shows that match the captured source by merchant, event ID and performance ID. It preserves their database IDs and relationships. The other 514 historical rows remain unchanged.

Three historical duplicate-identity pairs remain untouched: 7451272/3769502 (Fire & Beer), 1371908/847662 (Spitball), and 927780/1024865 (God Lens Book Release Show & Party). Their stored dates differ and they are outside the current inventory. This task does not consolidate them or infer which historical date was authoritative.

## Design and activation

Source-identified shows use a namespaced provider identity scoped to the actual club. Legacy shows retain their physical club/date/room uniqueness. Identity is carried through conversion, deduplication, upsert result matching and persistence so ticket and lineup rows attach to the correct show even when two performances share an instant.

ThunderTix activation is explicitly scoped to reviewed sources. Annoyance source 53 is activated only after its existing matching rows are backfilled. Other sources retain the previous behavior until separately reviewed. The shared nullable identity field can support SeeTickets in TASK-4080, but does not establish cancellations or venue assignments for Port's ambiguous source listings.

The migration replaces the unconditional physical unique index with two disjoint partial unique indexes. Old scraper workers must not run across this schema transition: their old ON CONFLICT clause cannot infer the legacy partial index. Validate against production-shaped rows, ensure no active scraper run, apply the schema, perform the guarded backfill, and use the updated scraper for refresh before allowing normal scheduled execution.

## Verification status

The schema migration was validated against production-shaped rows and applied while no GitHub scraper run was active. The guarded repair then backfilled all 210 reviewed identities and activated source 53 atomically. A dry-run first exposed the production source updated_at trigger; the transaction rolled back and trigger-aware validation was added before the successful dry-run and apply. The private recovery snapshot is stored outside Git and must not be published.

Two normal scraper runs completed on September 30 at 20:23 and 20:28 America/New_York. Each produced all 275 eligible performances. The first inserted 65 and updated 210; the second inserted zero and updated 275. The database now contains 789 Annoyance shows. Both runs retained the same identity-to-show-ID mapping, including all 76 simultaneous performances in 38 slots. No room labels were fabricated.

Post-run database verification preserved all 724 original show IDs and all original relationships: 724 tickets, 15 lineup items, 1,885 tags, and 6,638 ticket-click records (the other three relationship tables had zero original rows). All 514 unreviewed historical show rows remained exactly unchanged. Public counts and identity mappings are in production-verification.json; private relationship rows are excluded.

Validation includes real PostgreSQL tests for simultaneous persistence, rescheduling, legacy coexistence, duplicate idempotence, reconciliation, guarded repair, rollback, restore, and source timestamp triggers. The core commit passed the full scraper gate; the fresh Prisma-generated CI schema plus the SQL-owned migration passed its PostgreSQL test set. CI now explicitly applies the partial-index migration because Prisma cannot express those index predicates.

The recovery command deliberately refuses to restore after subsequent refreshes have changed the saved after-state. A recovery after these verified refreshes requires a newly reviewed plan. Restore preserves business data but the database trigger advances scraping_sources.updated_at.
