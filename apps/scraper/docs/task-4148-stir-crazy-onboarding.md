# Stir Crazy Comedy Club onboarding

The official Glendale venue is https://www.stircrazycomedyclub.com/ at
6751 N Sunset Blvd, Ste E-206, Glendale, AZ 85305. Reuse canonical club
17393; its existing hidden record has no enabled first-party calendar source.
Its timezone is America/Phoenix (UTC−7 throughout the year).
The official footer's https://goo.gl/maps/4AvsPkTiqCMepCUc8 redirects to the
venue place at latitude 33.5335572, longitude -112.2616635 (the destination's
place coordinate fields, not an inferred city center). Use those coordinates
to fill the canonical record's currently missing location.

The official calendar is a custom ASP.NET application. Its public site JavaScript
posts JSON to Services/Services.asmx/GetMaxMonths and
Services/Services.asmx/GetUpcomingShowsByMonth. The latter receives integer Month
and Year fields and returns the ASP.NET d wrapper, a success flag, and
Result.CalendarDays[].CalendarItems[]. The UI horizon includes the current month
through the GetMaxMonths offset, crossing year boundaries as necessary.

Native October 2026 evidence contains 36 performances. Calendar DateLabel and
MilitaryTime are authoritative; ItemNumber is an opaque identifier, not a clock:
Monroe Martin's 2026100919 performance actually starts at 18:00. Calendar prices
are default projections (zero), not ticket prices. The event detail supplies
performance-specific JSON-LD startDate, offers and performers, corroborated by
the ticket selector. Monroe Martin has four performances October 9–10 at 18:00
and 20:30, with $25 tickets.

Use the existing native HTTP stack and browser-style Referer/X-Requested-With
headers. A successful HTTP status alone does not prove a valid response: observed
headerless API requests returned d:null. Validate the envelope and every required
month/detail before emitting a complete result. Preserve sold-out performances,
exclude non-performance products/classes/private events, and do not infer prices
or showtimes from calendar defaults or identifier suffixes.

Source activation preserves the venue identity and hidden state. Enable public
visibility only after successful persistence of verified upcoming performances.

## Verification completed October 10, 2026

Applied source migration 20261009180000, then the separate dated performer
correction 20261010010000. The initial name-based command excludes hidden
venues, so first ingestion used `make scrape-club-id ID=17393` while hidden.
After verified persistence, migration 20261010020000 enabled visibility with
guards requiring the enabled source and future native shows with ticket URLs.
Confirmed the UPDATE affected the canonical club: visible=true, HTTPS website,
America/Phoenix timezone, verified coordinates, and one enabled native source.
The migration runner reports no pending migrations on rerun.

A fresh native-stack comparison fetched all five calendar months and 64 detail
pages: 115 performances from October 10, 2026 through February 10, 2027,
117 ticket options, and 177 lineup entries exactly matched persisted records.
There were zero missing, extra, or mismatched title/local-time, ticket
URL/price/type, or lineup values. The earlier probe included a now-past October 9
performance; the live calendar added February 10 Open Mic before ingestion.

Ilya Axelrod November 11 at 20:30 has GA $60 and VIP Front Row $100 on one show.
Comedy Hypnosis November 22 at 18:00 has GA $20 and VIP $30 on one show.
Monroe Martin October 10 remains two distinct performances at 18:00 and 20:30,
each $25 with Monroe Martin, Mike Harris, and Ron Morey in the lineup.
Public open mics and class showcases remain included. Thanksgiving's explicit
No Show Tonight closure, private events, gift products, and instructional
classes are excluded. Boilerplate Person schema does not turn generic show
titles into comedian profiles; ambiguous programs use verified date-bound
metadata overrides, which cannot carry old casts into a reused future slug.

After publication, `make scrape-club CLUB='Stir Crazy Comedy Club'` succeeded.
The complete second DB snapshot exactly matched the first: 115 identical show
IDs, 117 ticket values, and unchanged lineups, with no duplicate performances.
The geography audit over 2,884 sources (including hidden clubs) returned no
Stir Crazy finding. All 28 focused regression tests and the scraper commit
test gate passed.
