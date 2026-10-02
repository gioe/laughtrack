# Gotham dated poster lineup recovery — TASK-4088

The live Webflow proxy feed is https://square-mountain-7159.alex-cdc.workers.dev/items. The October 1 capture contains 435 items and 16 unique image URLs associated with October 1 or later events. All 16 assets were downloaded and visually inspected using printed text only; no faces were identified. Source item fields, image URLs, SHA-256 hashes and visual classifications are recorded in `source-evidence.json`.

## Current source evidence

- Show 6972715, Gotham All-Stars, October 1 at 8 PM New York time: Nathan Macintosh, Dean Edwards, Dan St. Germain and Kunal Arora are printed on the attached poster.
- Show 6673899, Comedy Spotlight, October 6 at 7:30 PM New York time: Rafi Bastos, Tim Dillon and Louis Katz are printed. “+ MORE TBA” means additional unannounced slots, not a fourth performer.
- Both current named posters have Gotham branding and date/showtime text. Main Room comes from their feed event context; neither image explicitly prints “Main Room.” Do not describe that room as independently printed evidence.
- All seven names match existing visible canonical comedian rows (parent_comedian_id is null) in the database. Both shows had empty lineups at the initial snapshot.
- Laugh for Sight retains an old poster advertising 8:15 PM and an unannounced full lineup, while the current feed has 8:30 PM and explicit named billing. Keep the current text-derived lineup; the poster does not authorize adding Brian Fischler or historical alumni.
- Mixtape's poster is undated and includes musical billing. Its named host is already recovered from explicit source descriptions by TASK-4087.
- The other twelve assets have no dated printed comedian lineup: generic logos, unnamed headshots, event branding or benefit information.

## Historical fixture

The six poster-only examples from TASK-4055 now refer to past events. Retained `../2026-09-26-missing-lineups/gotham/poster-5509344.png` explicitly prints Saturday September 26, 7 PM, The Vintage Lounge, Peter Revello, Leclerc Andre, Erin Jackson, Vlad Caamano and Teressa DeGaetano. Its printed weekday matches 2026; it serves as a captured positive fixture, not evidence for a current show.

## Extraction infrastructure

No reusable image-text extraction implementation was found in the scraper, web application or installed gioe_libs package. Scheduled scraper jobs and CI already install Tesseract plus English language data. This task uses that existing executable and the existing Pillow dependency, with actual image validation locally. Decorative lettering makes raw full-image OCR unreliable, so successful OCR alone does not authorize a new comedian identity.

## Later source update during verification

A second live read later on October 1 found that the Laugh for Sight description had been updated to explicitly list Brian Fischler, Cory Kahaney, Peter Revello, Mike Yard, Mark Normand, Aaron Berg and host Shaun Eli. The existing TASK-4087 text parser correctly recovers all seven. `later-laugh-for-sight-source.json` retains that new source item. The earlier warning remains about the stale poster being insufficient evidence on its own; it is not a prohibition against Brian Fischler when newly billed in current text.

The integrated read-only scrape returned 112 upcoming shows with prices, five named shows and 16 memberships: seven from the two validated posters, seven from the updated Laugh for Sight text, and one host for each of two Mixtape events. No scrape error occurred.

The live ticket price for Comedy Spotlight is now $35 versus the stored $25. This task's targeted repair adds only validated lineup memberships, leaving ticket updates to the normal scraper pipeline.

## Ongoing safeguards and limits

The supported layouts are Gotham's square caption grid (Main Room or explicit Vintage Lounge) and the portrait Comedy Spotlight caption row. Other artwork is left unknown. The parser crops only printed date, room/branding and name rectangles; it does not identify faces or infer names from show titles. Month/day, weekday and showtime must agree with the event in America/New_York. A printed year must agree; when omitted, the year is supplied by the attached feed event and checked against the printed weekday. This does not independently prove the year of an undated-year asset.

Each name requires a unique exact normalized match to an existing canonical database comedian. Hidden matches, aliases that cannot be corroborated exactly, ambiguous identities and deny-listed names are excluded. An unavailable DB or OCR engine produces no poster memberships. This intentionally does not discover new comedians or fuzzy-correct misspelled names. Existing explicit text billing takes precedence over posters.

Enrichment happens after all fetched feed pages arrive, before transformation. Assets reused across different event identities or room contexts are rejected, including identical bytes at different URLs. Only HTTPS assets on the source's S3 host are fetched, without redirects. Each scrape attempts at most 32 unique URLs, allows 5 MB and 4 million pixels per image, uses a 10-second fetch timeout and a 3-second timeout per OCR crop, and stops starting more work after a 120-second budget. The in-flight operation can finish after that budget; it is not a hard process deadline. URL and content-hash caches include negative results and are local to that scrape.

## Production repair and verification

The repair added only source-verified `(show_id, comedian_id)` memberships, with transaction-time checks of show identity and existing visible canonical, non-denied comedians. It used idempotent inserts and did not remove memberships or update shows, tickets or comedian records.

All seven expected memberships are now present on shows 6972715 and 6673899. Six were inserted by this repair; one had already arrived through concurrent production ingestion. All 609 original show IDs and 609 original ticket IDs remain present, and both repaired show identities/date/room/source URLs are unchanged.

Production was active during verification: four additional shows appeared, and 108 original rows differed from the earlier snapshot, including ordinary refresh timestamps and source updates. Those changes must not be attributed to this repair. `verification.json` records the differences; `repair-result.json` records the exact membership-only write result. The targeted write did not update the separately changed Spotlight ticket price or Laugh for Sight text lineup.

Validation: all 88 Gotham tests pass, including real Tesseract runs on both current posters and the retained Vintage fixture, captured TSV replay, wrong date/time/year/weekday/room, unreadable room, repeated URL/content, generic/TBA-only artwork, failed extraction, resource bounds, and canonical/deny-list corroboration. The full scraper commit gate passed in 87.2 seconds. Real OCR of all 16 current assets produced candidates only for the two named dated posters.
