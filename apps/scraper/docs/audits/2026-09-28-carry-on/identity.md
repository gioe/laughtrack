# Carry On identity investigation — TASK-4066

Cutoff: 2026-09-28T14:46:00Z. Read-only evidence captured September 28.

The official Carry On site and SeatEngine venue 584 describe an airline-themed cocktail experience in Phoenix, not comedy programming. Google Places confirms Carry On at **2 N Central Ave #101, Phoenix, AZ 85004**, coordinates **33.4486014, -112.0749021**, primary type cocktail_bar, website carryonphx.com. The configured source explicitly uses America/Phoenix.

The stored New Rochelle address and coordinates exactly match **Marshalls & HomeGoods**, Google place ChIJG0Jn64qNwokRGYoxmO3p3Xk. The correct Carry On place is ChIJZTvexEQTK4cRhKU-6MI20DU. This is a wrong business match, not a venue relocation. No other club matched the Carry On name or Phoenix street address. Do not deny-list the unrelated New Rochelle place on Carry On evidence.

All **38 upcoming stored shows** join to the successful SeatEngine API by exact source-show ID and UTC start; each belongs to venue 584 and event WELCOME ABOARD. The API currently returns 66 sessions. Original task evidence counted 55 upcoming rows on September 24; time elapsed, so this audit uses the fixed current cutoff. Official ticket links and current API are positive evidence; old detail-path 404s do not establish cancellation.

The database contains 713 total shows, 1,788 tickets, 1,566 show tags, 136 scraper-run references and 4,308 venue-linked purchase-click records (4,276 linked to these shows). There are no lineup rows, saved shows or venue favorites. before.json records all discovered direct club/show foreign-key counts and row digests; no private click payloads are exported.

## Reviewed repair

Keep club 600 and source 336 stable. Correct the address, postal fields, coordinates, Google place and timezone. Mark the operating venue hidden/non_comedy, retain active status, and disable its SeatEngine source with task_4066_disposition metadata. Deny only the verified Phoenix place. Preserve every show and dependent reference, including stored UTC timestamps; no event is reassigned or deleted.

Existing national SeatEngine upsert preserves disabled sources with a task disposition key; removing the source would lose that protection. Existing public query gates exclude hidden venues from search and show details. The authoritative branch is exclusion from comedy discovery, not moving cocktail reservations into Phoenix comedy results.

Evidence: places.json contains both business identities; source-evidence.json contains all 38 joins and source URLs; before.json preserves original fields and dependency counts. Public pages were fetched through HttpClient/curl-cffi; raw HTML and access-bearing ticket-link tokens are not committed.
