# Ann Arbor Comedy Showcase coverage — TASK-4147

## Confirmed diagnosis (2026-10-09)

Production club 16122 is Ann Arbor Comedy Showcase, 212 S 4th Ave,
Ann Arbor, MI 48104, timezone America/Detroit, website
https://www.aacomedy.com. No duplicate club or alias was found.
Its enabled source 7682 is Etix, scraper key etix, URL
https://www.etix.com/ticket/v/515/ann-arbor-comedy-showcase, with empty metadata.
The official homepage still links Etix venue 515: the platform identity is correct.

Production had zero upcoming shows. The latest two runs failed with zero shows,
HTTP 403 and playwright_datadome diagnostics. Native scraper HTTP/browser probes
of the Etix source, upcomingEvents venue endpoint, and Sklar Brothers series
returned DataDome challenges (including banned-IP evidence). This is an access
failure, not evidence that the venue stopped booking shows.

The native official homepage was accessible. Its featured Jay Stevens section
explicitly advertised October 8 and 9 at 7:15pm, and October 10 at 7:15pm and
9:45pm. The matching event card links Etix series 1059733, slug stevens26, and
corroborates the October 8/9/10 dates. The remaining Duda event cards give dates
without performance times; their month/day badge fields are stale placeholders.
JSON-LD contains venue identity, not performances. The full-calendar button leads
back to the blocked Etix venue page.

## Chosen source

Keep source 7682 and its HTTPS Etix URL enabled and unchanged. Add a narrowly
scoped official-homepage highlights fallback for this club and venue ID only.
Use explicit featured showtimes with matching card/date/ticket/year evidence;
do not generate shows from generic weekly hours, doors, untimed cards, gift cards,
classes or happy hours. The fallback is incomplete: preserve failure diagnostics
and prevent stale reconciliation even when it recovers shows. A healthy Etix
response continues to use the existing complete-calendar parser.

The accessible evidence supports four Jay Stevens performances, of which three
were upcoming at verification time. Full-calendar recovery remains limited by
Etix access; this fallback must never be described as complete inventory.
