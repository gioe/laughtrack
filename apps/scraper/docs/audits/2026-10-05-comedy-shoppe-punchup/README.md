# Comedy Shoppe source recovery — TASK-4112

## Reproduction and current source

On October 5, club 327 had zero upcoming shows. Enabled source 617 still used
ShowSlinger widget 238, which returned the explicit no-tickets message. The official
calendar at https://www.jjcomedy.com/socials instead contains PunchUp hydration for
page `4969662d-af53-4d87-b151-9f94c8f89d4c` / slug `comedyshoppe`. The old shared
extractor returned 20 events from its first successful carousel match; decoding the
complete page yielded 24 unique event IDs. `current-projection.json` records the
public event/location fields and the fetched HTML hash, without full biographies,
backend contact data, or the old ShowSlinger secure code.

The public API supplies additional inventory:

- `/api/shows?venuePageId=4969662d-af53-4d87-b151-9f94c8f89d4c&limit=20&offset=0`: 20 rows.
- The same request with offset 20: 7 rows.
- Offset 40: 0 rows.

The API host is `https://punchup.live`; the endpoint shape was checked against the
existing Side Splitters implementation and directly fetched using the scraper's
curl-cffi HTTP stack. `paginated-projection.json` records all 27 IDs and preserves
native dates, ticket URLs, and venue associations. The page alone is not proof of
completeness. The scraper must reach a short API page; a failed page or pagination
limit remains an incomplete result that cannot authorize reconciliation.

## Performance boundary

The API adds Gabriel Rutlege's April 23, 2027 21:30 performance at Newtown Theatre,
plus two listings of **The Day Players at Wonders Theatre** on February 19–20.
The latter are explicitly music: native description says “join us for a concert
with VIP meet and greet” and identifies an acoustic band. Their native IDs are
`b4f2de4c-f11a-4d3c-b165-005df9e2941b` and `9b40355b-ee1b-4314-90ab-5dacf41ecb8b`.
The reviewed source-scoped title exclusion removes these two concerts; it is not
a global rule or an inference from generic title words. Expected current comedy
inventory is **25 performances**. The original September 28 captured set of 24
remains a regression fixture evaluated at its original date; it is not today's
hardcoded expected inventory. Current successors also include changed dates/times,
which must remain attached to their native event identity.

## Physical venue review

The official page publishes seven native physical locations with complete street,
city, state, and ZIP. Their IDs and addresses are unchanged from the September 28
audit. The current 27 events use four of those locations: Big Shots Restaurant &
Lounge (NJ), Dreamers Restaurant (SC), Newtown Theatre (PA), and Wonders Theatre
(SC). Mauch Chunk Opera House, Arcadia Clubhouse, and Bloomsburg Theatre Ensemble
remain reviewed locations in the page, without current events in this snapshot.
All seven routes use America/New_York; no performance is assigned to the legacy
organizer's unrelated 167 Bleecker Street address in NYC.

Exact and broad name/address searches found no existing destination matches.
Candidate clubs 76800 (Arcadia bar in England), 20422 (Fargo Theatre), and 8896
(SB Comedy Hideaway in California) were rejected as different physical locations.
New venues are source-less physical identities. Their website is left blank when
no independent venue website was verified; the source and producer retain the
verified HTTPS organizer website/calendar. Runtime routing compares the live native
address and the stored destination against the reviewed route, and holds missing,
conflicting, or unavailable locations.

## Cross-platform duplicate review

Exact current and original ticket URLs were checked against every stored
shows.show_page_url and tickets.purchase_url, not only club 327. No matches were
observed in the initial HTML inventory check; activation independently rechecks
all 27 paginated URLs under locks. Broad destination identity searches also found
no hidden existing venue match. A separate global title-word search within one
hour of each of the 27 local dates (converted using America/New_York) returned
48 candidates. All were different performers or generic Christmas/New Year's
phrases at different physical venues. `duplicate-check.json` preserves these
candidate rows and dispositions. This is bounded evidence, not a guarantee about
arbitrary unrelated future platform feeds.

## Activation and provenance

`activation-plan.json` uses full-row hashes for the source and organizer instead
of publishing the old secure-code URL. The guarded one-shot activation creates
the reviewed physical venues and a production-company identity, then changes only
source 617's platform, implementation key, calendar URL, and metadata. Platform
`custom` is used because the current enum has no PunchUp member. The legacy source
configuration is retained privately in the activation marker and recovery snapshot.

The legacy club 327 identity and visibility remain unchanged so the enabled source
continues to be discovered. All new performances carry the real producer FK and
physical destination club. Source targets and all existing shows/dependencies are
preserved. The script requires a durable private backup before apply, validates
before-images under locks, checks duplicate URLs and title/date candidates, and
is idempotent. Never commit the private backup or unredacted old source URL.

Production apply, live-scrape verification, and test results are recorded in
`verification.md` once executed. The original source scope has no data-deletion
operation; rollback of newly ingested shows requires separate dependent-aware
review rather than blindly removing venues with references.
