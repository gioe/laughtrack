# TASK-4084: Comedy Clubhouse public calendar recovery

## Current failure and source contract

Club 189 / source 623 had 85 historical records and no upcoming shows. [Runner 36887941353](https://github.com/gioe/laughtrack/actions/runs/36887941353), using commit 6d5f396c6 and the scheduled credentials, reproduced HTTP 403 / Cloudflare followed by a browser access-denied page: zero shows, success=false and fetches_failed=1. See baseline-runner.json.

The [official Chicago venue](https://www.thecomedyclubhouse.com/) links to the TicketSource .us organizer calendar. Both .us and configured .com calendars were accessible with the actual local scraper HTTP stack on October 1, but local availability did not establish runner access. The public page identifies organizer KEGG, 12 events per load and a nonterminal initial page. Its linked [promoter-list script](https://www.ticketsource.com/ticketshop/web/v7/promoter-list-detailed.min.js) posts to /ticketshop/web/promoter-list-detailed_ajax.php with promoterid, localtimeoffset, eventrefno and startat. This is the calendar's own public listing endpoint; no private credentials, alternate identity, proxy rotation or invented API was used.

The API's organizer credential requirement is distinct: TicketSource's [authenticated account API](https://www.ticketsource.io/getting-started) requires an account API key. This change uses the public website endpoint, not that private API.

## Verified public inventory

Public POST requests for organizer KEGG at offsets 1, 13, 25, 37 and 49 returned 12, 12, 12, 12 and 11 performances. The last response explicitly has eof=true. That is 59 individually dated performances through March 20, 2027, with Chicago venue identity, per-performance detail links and booking links. Each structured timestamp agrees with the dated performance URL. These are advertised listing start times, not dates expanded from recurring programming or doors times. No inferred 30-minute delay is added to the venue's advertised starts.

A bounded probe at the next offset, 61, returned HTTP 200 and exactly {"eof":true}. This captures the endpoint's terminal-empty contract; it does **not** show that the live venue calendar is empty. Empty success requires this verified envelope or an explicit boolean eof with an empty events array, scoped to the verified organizer. Blocked HTML, malformed envelopes, missing/false EOF, truncated nonterminal pages, repeated IDs/booking links, conflicting same-time identities, invalid dates and unexpected venues fail the entire calendar and prevent stale reconciliation.

Actual public response fixtures are retained beside test_verified_calendar_states.py. public-feed-fetches.json records request offsets, capture times and response hashes; source-evidence.json records the homepage/calendar/script evidence. Unknown prices remain null. The source row remains unchanged.

## Implementation and validation

The venue-specific scraper uses existing post_form for the published endpoint, with 30 seconds per request and a 20-page limit. Only club 189 with the known TicketSource organizer URL and America/Chicago timezone uses this path. Legacy HTML extraction remains supported but refuses a page advertising unconsumed pagination. No calendar is considered complete merely because all 12 visible HTML rows parsed.

The focused suite passes 49 tests. The actual read-only scraper returned all 59 shows with fetches_ok=1, fetches_failed=0 and no scrape errors; see readonly-preview.json. Scheduled runner persistence remains to be verified before completion.
