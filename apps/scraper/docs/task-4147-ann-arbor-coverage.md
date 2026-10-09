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

## Production verification (2026-10-09)

Ran `make scrape-club CLUB='Ann Arbor Comedy Showcase'` from the task worktree's
`apps/scraper`, with its source directory on PYTHONPATH. Run 1711 inserted four
shows. Run 1712 added the explicitly corroborated performer lineup; run 1713
repeated the final implementation with zero show inserts and four updates.

| Show ID | Local date | America/Detroit time | Lineup |
|---|---|---|---|
| 8128083 | 2026-10-08 | 19:15 | Jay Stevens |
| 8128084 | 2026-10-09 | 19:15 | Jay Stevens |
| 8128085 | 2026-10-10 | 19:15 | Jay Stevens |
| 8128086 | 2026-10-10 | 21:45 | Jay Stevens |

All four have one ticket linking https://www.etix.com/ticket/e/1059733 and
unknown price (NULL). After the repeat, production still has four show IDs,
four tickets and four lineup rows for this venue, with three upcoming shows.
The older Thursday performance is retained as historical inventory. The source
remains the single enabled row 7682, unchanged; no identity/configuration
migration was needed. Existing HTTPS website and Detroit timezone are correct.

All three run records retain HTTP 403, DataDome detection and one failed fetch
alongside the recovered shows. The fallback records incomplete diagnostics so
stale reconciliation cannot delete inventory merely absent from the highlights.

Untimed listings including Sklar Brothers, David Dyer, Comedy Rumble, Andy
Hendrickson and Nate Craig remain a coverage gap, not cancelled performances.
Workshop classes, gift cards and happy hour are legitimate non-show exclusions.
Complete future-calendar recovery requires a trustworthy accessible source with
event-specific times; generic weekly hours cannot fill this gap.
