# The Comedy Clubhouse source audit — 2026-09-26

TASK-4053; Chicago club 189, enabled source 623 (`comedy_clubhouse`).

## Findings

The official https://www.thecomedyclubhouse.com homepage identifies the venue at
1462 N. Ashland, Chicago, IL 60622 and links to
https://www.ticketsource.us/thecomedyclubhouse. Its general improv/stand-up/scripted
comedy description is not evidence of current dated performances. It exposes no
individual Event JSON-LD or alternate embedded calendar.

Both that `.us` URL and the configured `.com` URL returned the same branded
Access denied / HTTP ERROR 429 body using the scraper's PlaywrightBrowser.
`source-evidence.json` records the method and response hashes;
`ticketsource-blocked.html` retains the observed vendor response.
The body reports 429; this browser probe does not capture an HTTP status code.
Production runs 1420, 1426, 1438, 1446 and 1468 independently recorded HTTP 403 and
Cloudflare `_cf_chl_opt`, but incorrectly marked the zero-output club successful.

## Fix and limitations

Mandatory fetch, challenge, parser, missing HTML, unrecognized zero-card and
incomplete-card failures now propagate as high-severity data errors. Failed
fetches protect existing inventory from stale-show reconciliation. Titles must
come from the event title element, not the venue's separate name element;
invalid performance dates fail the calendar before transformation.

No verified empty-calendar markup was accessible. Zero-card responses therefore
remain failed/unverified until an authoritative venue-specific empty state can
be captured. We do not claim the venue is dark. The existing supported event-row
format still extracts, while regression tests exercise blocked bodies, transport
failure, partial extraction and invalid timestamps through actual fetch diagnostics
and reconciliation eligibility.

Changing `.com` to `.us` alone does not recover inventory. No configuration or
inventory migration is justified by these results. Next action: obtain an approved
TicketSource calendar feed or vendor access for the scheduled runner, verify dated
performances and an explicit empty state, then rerun single-club verification for
club 189 before declaring source recovery.

## Validation

Focused pipeline suite: 25 passed. Scheduled runner evidence will be recorded
below after verifying the committed change with the production scraper setup.
