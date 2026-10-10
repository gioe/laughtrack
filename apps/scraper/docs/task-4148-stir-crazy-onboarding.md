# Stir Crazy Comedy Club onboarding

The official Glendale venue is https://www.stircrazycomedyclub.com/ at
6751 N Sunset Blvd, Ste E-206, Glendale, AZ 85305. Reuse canonical club
17393; its existing hidden record has no enabled first-party calendar source.
Its timezone is America/Phoenix (UTC−7 throughout the year).

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
