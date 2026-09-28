# AC Jokes and Pagliacci venue audit — 2026-09-28

Fixed upcoming cutoff: `2026-09-28T13:45:00Z`. Read-only production queries and public-source retrieval. No scraping pipeline/persistence execution or production writes. Convention search `tusk conventions search "venue routing"` returned rule 251: organizer feeds route per event, collection scrapers need explicit routing support.

| Producer | Configured club / source | Upcoming DB rows | Correct | Confirmed mismatch | Unknown |
|---|---|---:|---:|---:|---:|
| AC Jokes | 412 / 291, Wix Events | 44 | 40 | 4 | 0 |
| Pagliacci | 8701 / 5852, Eventbrite organizer 68051880803 | 0 | 0 | 0 | 0 |

## AC Jokes

Current Wix feed returns exactly 44 events, total=44, hasMore=false, in one page. All 44 match a production show by exact URL slug and exact UTC start time; none route to another club. Source JSON retains event UUID, title, slug, timestamp and complete location but strips unrelated payload and authentication. `per-show.json` contains the complete row-level classification and retrieval timestamps.

Forty events are correctly assigned to club412, 1133 Boardwalk, Atlantic City NJ08401: both Starlight Ballroom and Directors Room are rooms at Resorts, not separate venue mismatches. All 44 detail URLs returned HTTP404 through the actual HttpClient; the successful public Wix API is the authoritative event evidence. This is not based only on stored room/title.

| Show ID | UTC start | Event location | Assigned club location |
|---|---|---|---|
|6537818|2026-10-05T01:00:00Z|Hi Point Pub, 5 N Shore Rd, Absecon NJ08201|1133 Boardwalk, Atlantic City NJ08401|
|7475796|2026-10-18T00:00:00Z|The Cove Restaurant, 3700 Brigantine Blvd, Brigantine NJ08203|1133 Boardwalk, Atlantic City NJ08401|
|6537828|2026-11-02T02:00:00Z|Hi Point Pub, 5 N Shore Rd, Absecon NJ08201|1133 Boardwalk, Atlantic City NJ08401|
|6537839|2026-12-07T02:00:00Z|Hi Point Pub, 5 N Shore Rd, Absecon NJ08201|1133 Boardwalk, Atlantic City NJ08401|

Ingestion trace (paths relative to repo): `apps/scraper/src/laughtrack/scrapers/implementations/api/wix_events/scraper.py:52` registers `WixEventsEventTransformer(club)` once using the configured source club. Lines57–124 request paginated Wix events. `.../wix_events/extractor.py:40` preserves each location. `apps/scraper/src/laughtrack/core/entities/event/wix_events.py:74` extracts only location.name into room and calls create_enhanced_show_base with the unchanged club. `apps/scraper/src/laughtrack/utilities/domain/show/factory.py:493` assigns club_id=club.id. Thus the source has correct physical addresses but persistence receives the organizer club ID.

Recommendation: add explicit per-event physical-location resolution to Wix organizer-style feeds, mapping normalized full address/name to physical clubs; preserve same-building Resorts room labels and producer attribution. Then repair exactly these four row assignments after resolving/creating Hi Point Pub and The Cove safely. Do not replace club412's address: that would break40 correct shows. A club-name/address discovery query found neither target venue (the similarly named Cove at River Spirit is Tulsa and must not be reused). This is a discovery result, not an exhaustive identity dedupe audit.

## Pagliacci

`pagcomclub.com` redirects to the Eventbrite collection3267469. Its JSON-LD lists18 historical events dated2023 or2025: Cafe Italiano at417 Clay Avenue, Jeannette PA15644 in2023; Manor Grill/200 Main Street, Irwin PA15642 in2025. These dates are before the cutoff; older Cafe Italiano cards do not establish a current address mismatch. The organizer page embedded `__NEXT_DATA__` explicitly says upcomingEvents=[], upcomingEventsTotal=0, hasMoreUpcoming=false, upcomingEventsFailed=false. The authenticated organizer API produced non-JSON, so current coverage relies on the successful public organizer payload rather than claiming API success.

No upcoming shows belong to club8701. Wider queries also found none by Pagliacci/Brothers-Grinn show name or URL, Cafe Italiano club name/address, or the18 historical collection event IDs. No production_company row matches this organizer ID or producer name, so organizer-attribution lookup cannot broaden membership further. There are no currently observed correctly routed alternative-club shows to list; the public organizer confirms zero upcoming events.

Source5852 URL includes `/o/`, so `apps/scraper/src/laughtrack/scrapers/implementations/api/eventbrite/scraper.py:175` activates organizer mode. `apps/scraper/src/laughtrack/core/clients/eventbrite/client.py:77` requests expand=ticket_availability,venue and lines241–251 select the organizer endpoint. Scraper lines375–384 group API events by venue; lines450–475 reuse/resolve/upsert physical venue clubs and call event.to_show(venue_club). This already supports proper venue routing. No evidence justifies a Pagliacci show reassignment or changing the current club address. Recheck when a new organizer event appears, particularly if Cafe Italiano returns; verify the event's own expanded venue.

## Scope queries

Production snapshot retrieved2026-09-28 around13:50–13:57Z. Upcoming condition was date > cutoff. AC/Pag primary query selected all base-club rows plus URLs matching acjokes, pagliacci, brothers-grinn; it returned44 all at412. Secondary query selected upcoming rows at clubs matching Italiano/Pagliacci, address417 Clay, or show names Pagliacci/Grinn; returned0. Exact18 Eventbrite collection-ID lookup across all shows/all clubs returned0. This prevents interpreting base-club zero as proof without checking the organizer source and routed candidates.
