# Catch a Rising Star, Princeton — source diagnosis

Inspected October 10, 2026. Canonical club 4744 is currently named Hyatt Regency
Princeton at 102 Carnegie Center, Princeton NJ 08540. All 16 stored historical
shows are Catch comedy; six are upcoming. Preserve this club ID and all inventory.
Its enabled Live Nation source 7814 and disabled Ticketmaster source 3834 both
retain venue ID rZ7HnEZa1D3. Do not enable the retired per-venue Ticketmaster fanout.

The official https://www.catcharisingstar.com/ homepage lists 11 Princeton acts
through December 26. It also includes two unrelated Massachusetts tour events.
Joomla detail pages supply dates and biographies but no performance times.
Their recurring agid values identify acts, not stable individual performances.

Official ticket links point to
https://www.ticketweb.com/venue/hyatt-regency-princeton-princeton-nj/44754.
The scraper's native PlaywrightBrowser fetched this page successfully (175,526
bytes), despite a direct HTTP attempt returning 506. The venue page contains 16
TheaterEvent JSON-LD objects matching 16 rendered event cards. Every remaining
Princeton homepage date is covered; the seventeenth date was yesterday. No next
page or load-more link is present. Six URLs match existing upcoming shows, leaving
ten missing performances. Exact source times vary: December 19 starts at 20:00,
whereas December 26 starts at 19:30. Local dates require America/New_York, including
the November daylight-saving transition. Offer URLs and availability are explicit;
prices are absent, so unknown prices must remain null.

Reuse json_ld with force_js_rendering and the exact Hyatt location-name guard.
Normalize only explicit performer labels using source-local aliases; TicketWeb
prefixes Eric Potts and Jill Myra with NJ 101.5 and Jackie Martling with promotional
text. Preserve explicit support acts and disable inference from event titles.

Use the recognizable display name Catch a Rising Star at Hyatt Regency Princeton
on existing club 4744, retaining Hyatt Regency Princeton as an exact locality
alias. ClubHandler resolves aliases, whereas public club search displays the
canonical name. Keep coordinates, timezone and aggregate sources intact; add the
HTTPS official website and the direct JSON-LD source idempotently.

## Deployment and verification

Applied 20261010130000_onboard_catch_rising_star_princeton.sql and verified
club 4744's branded name, HTTPS website, unchanged New York timezone and location,
two verified aliases, and enabled JSON-LD source 14961. Live Nation 7814 remains
enabled; retired Ticketmaster 3834 remains disabled. No new venue was created.
The migration runner reports no pending migrations on rerun.

The actual JsonLdScraper.scrape() path returned 16 performances using native
Playwright rendering. Then ran
`make scrape-club CLUB='Catch a Rising Star at Hyatt Regency Princeton'` twice.
All 16 persisted timestamps and purchase URLs match the native calendar. All six
baseline IDs survived unchanged; ten previously missing performances were added.
There are 16 ticket rows and 24 lineup entries, matching explicit source acts
(case-insensitively for canonical names such as Gary DeLena). Promotional prefixes
are removed before comedian matching. Unknown prices remain NULL.

Both full persisted snapshots match exactly: show IDs, titles, timestamps,
purchase URLs, ticket types/prices, and lineups. No duplicates were introduced.
October uses UTC-4 and November/December UTC-5; the December 19 20:00 exception
is preserved. The two Massachusetts tour events on the brand homepage are outside
the Princeton source, and the October 9 performance is past. No advertised future
Princeton date was omitted.

Nine new regression cases plus 43 existing JSON-LD tests passed. The full scraper
commit gate also passed. A geography audit over 2,885 sources, including hidden
venues, produced no finding for club 4744. Source options are documented in
SCRAPERS.md and default behavior for other JSON-LD sources remains unchanged.
