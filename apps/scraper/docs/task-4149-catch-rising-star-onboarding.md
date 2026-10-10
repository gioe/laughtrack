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
