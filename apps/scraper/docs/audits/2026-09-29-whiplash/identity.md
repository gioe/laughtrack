# TASK-4067 — Whiplash identity review

Reviewed 2026-09-28; refreshed before repair 2026-09-29.

## Decision

Club 1347 / source 591 / SeatEngine venue 650 is **Whiplash Comedy at Ponce City Market, Atlanta**, not Brooklyn's Union Hall. This is a corrupt venue association, not evidence of a move from New York. Retain the Whiplash club ID, enabled source and all existing show/reference IDs.

Use **650 North Avenue NE, Suite S210, Atlanta, GA 30308, USA**, timezone America/New_York. The tenant's official JSON-LD supplies street/suite and Atlanta/GA, but incorrectly lists 30080. The landlord independently confirms Ponce City Market and its complex ZIP 30308. A Google address lookup of the exact NE street identifies **Ponce City Market Service Building**, ZIP 30308, at **33.7713365, -84.3667376**. These are building-level coordinates, not a verified suite entrance.

Clear the unrelated Union Hall Google place ID and photo attribution. Name-based Google searches returned no Whiplash listing. Do not replace it with the building's place ID, City Winery's ID, or an inferred Whiplash ID. No club image or image assets exist to migrate. Record the coordinate precision and unresolved business place ID in this audit; keep the public description readable.

## Evidence and rejected matches

- Official: https://www.whiplashcomedy.com/ — EventVenue address Atlanta, 650 North Avenue Suite S210; current shows are at the same venue UUID.
- Landlord: https://poncecitymarket.com/directory/whiplash-comedy/ — Whiplash is the Atlanta comedy tenant; complex mailing address is 675 Ponce De Leon Ave. NE, Atlanta GA 30308. Do not substitute that mailing street for the tenant entrance.
- SeatEngine: https://services.seatengine.com/api/v1/venues/650 — Whiplash, same website, Atlanta/Ponce City Market description, America/New_York timezone.
- Existing Google ID ChIJ43tYfapbwokRnkJq38aBk_M resolves to **Union Hall**, 702 Union St, Brooklyn NY 11215, unionhallny.com. Union Hall has its own club row 9; neither that club nor its place identity should change.
- Exact NE address resolves to Ponce City Market Service Building, ChIJxfSSVxAE9YgRN-t7Ed2RK7o. Accept its postal/coordinate evidence only, not as Whiplash business identity.
- An underspecified search without NE incorrectly returns 650 North Ave S210 in ZIP 30354, over 10 km away. Reject it: it is not Ponce City Market. This illustrates why the first Google result alone is insufficient.

## Shows and references

The refreshed feed contains four current performances; all four stored upcoming rows match SeatEngine venue 650 by exact source show ID and UTC start time (see source-evidence.json). The source changed its schedule between Sept 28 and Sept 29; refreshed evidence supersedes the earlier 13-upcoming snapshot. Current inventory is 26 shows, 48 tickets, 14 lineup items, 56 show tags, three comedian home-club references and 138 scraper-run references. Before.json inventories every FK to clubs/shows using counts and hashes, including click records without exposing user data.

Historical rows use the Whiplash source domain; some have test-event titles. Their historical occurrence is not established by today's feed. Preserve them and all comedian references; this task corrects venue identity, not historical deletion or performer curation. Existing production metadata attributes city/state parsing to TASK-3029. The original selection of Union Hall is not proven, so do not claim a particular script caused it.

## Scope and recurrence

Only the nine reviewed club identity fields change. Source ownership, enabled state, visibility, timezone, show dates and foreign keys stay intact. The actual SeatEngine upsert preserves populated location fields. Separate photo sourcing can overwrite Google place identity; the geographic auditor currently supports only Ticketmaster/Eventbrite for authoritative source resolution. File focused prevention follow-ups after deduplication.
