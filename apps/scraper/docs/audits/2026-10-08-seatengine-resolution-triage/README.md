# TASK-4133 — SeatEngine resolution failure triage

Read-only recheck on October 8, 2026 UTC (October 7 EDT), covering exactly the
15 source IDs flagged by TASK-4114. [results.json](results.json) records every
configured venue ID, native API response, website attempt, timestamp, sanitized
excerpt, classification, and next action. [verification.json](verification.json)
records independent verification of the unchanged source and club rows.

## Findings

| Outcome | Sources | Interpretation |
| --- | --- | --- |
| API returns HTTP 200 with data:null | 246, 431, 598, 631 | Identity unavailable; not a transport failure. Stale IDs, retired records, and API/classic incompatibility remain unresolved. |
| API returns HTTP 500 with Server Error | 371 | Repeated venue-specific API failure; configured events page remains reachable. |
| API-listed website fails DNS | 74, 82, 134, 441, 571, 637, 644 | Both curl-cffi and native Playwright fail on the exact hostname. No venue closure or replacement identity established. |
| API-listed website fails TLS hostname validation | 77, 268 | Both HTTP stacks reject certificate-name mismatch. No certificate bypass used. |
| Native URL scheme normalization failure | 594 | Exact Http:// URL becomes a malformed URL; changing only scheme case fetches the same domain successfully. |

None of the original failures recovered spontaneously during these checks.
Source 594 recovered only under the explicit scheme-case control. No platform
migration or geographic correction is confirmed. These categories describe the
observed failure boundary, not a guess at the venue's location or business status.

Two API identities also disagree with the stored club label:

- Source **77**, club **88** (Barrel Room Portland), configured venue **324**:
  API returns **Bridgeport** and a legacy experimental SeatEngine hostname.
  The configured Barrel Room events page has Eventbrite organizer links. That
  supports a platform-use investigation, not a replacement numeric identity or
  proof that a migration is complete.
- Source **134**, club **129** (StandUpLive Phoenix), configured venue **336**:
  API returns **Summer of Sass Inaugural Fundrasier**. The configured Phoenix
  events page is reachable and has classic SeatEngine markers. Matching the
  requested numeric ID is not enough to establish agreement with the club.

## Per-source disposition

| Source / club | Configured venue | Native API or API-listed website outcome | Next action |
| --- | --- | --- | --- |
| 246 / 45 — Stress Factory | 310 | API data:null twice; configured New Brunswick events page HTTP 200 | Independently establish the live site's numeric platform identity; preserve current configuration meanwhile. |
| 631 / 46 — Stress Factory Bridgeport | 311 | API data:null twice; configured Bridgeport events page HTTP 200 | Same identity verification, without deriving an ID from a logo or venue name. |
| 371 / 71 — Comedy Loft of DC | 298 | API HTTP 500 twice; configured events page HTTP 200 | Retry later or report the exact failing endpoint to SeatEngine; do not assume a stale ID. |
| 431 / 127 — Snappers Palm Harbor | 587 | API data:null twice; configured events page HTTP 200 | Verify native identity independently before any source/resolver change. |
| 598 / 130 — Stress Factory Valley Forge | 601 | API data:null twice; configured events page HTTP 200 | Verify native identity independently before any source/resolver change. |
| 77 / 88 — Barrel Room Portland | 324 | Bridgeport identity; legacy website certificate mismatch | Prioritize identity review and investigate Eventbrite links on the configured page. |
| 134 / 129 — StandUpLive Phoenix | 336 | Summer of Sass identity; API website DNS failure | Prioritize identity review; do not substitute a guessed Phoenix venue ID. |
| 74 / 389 — Wiseguys Jordan Landing | 367 | Legacy jordanlanding.wiseguyscomedy.com fails DNS | Verify authorization of the reachable configured West Jordan page as the canonical pointer. |
| 644 / 390 — Wiseguys Salt Lake City | 361 | Legacy downtown-slc.wiseguyscomedy.com fails DNS | Verify authorization of the reachable configured Showroom page. |
| 637 / 391 — Wiseguys Historic Ogden | 366 | Legacy historicogden.wiseguyscomedy.com fails DNS | Verify authorization of the reachable configured Ogden page. |
| 268 / 479 — Riddles Comedy Club | 455 | www.riddles.seatengine.com certificate mismatch; configured pointer also fails | Obtain a currently authorized platform/site identity; do not simply remove www or disable TLS verification. |
| 441 / 548 — Krackpots Comedy Club | 524 | www.krackpotscomedyclub.com fails DNS; configured krackpotscomedy.com page works | Verify canonical pointer binding before a separate pointer repair. |
| 594 / 551 — Deaf Puppy Comedy Club | 531 | Mixed-case scheme fails; same domain with lowercase scheme returns HTTP 200 | Separate shared URL normalization fix with a mixed-case scheme regression; no venue/source repair needed for this finding. |
| 82 / 562 — Hickory Premier | 542 | www.comedyzonehickory.com fails DNS; configured pointer also fails | Ask venue/platform for authorized current identity; closure and migration remain unresolved. |
| 571 / 850 — Bananas Comedy Club | 294 | bcccme.com fails DNS; configured bananascomedyclub.com page works | Verify canonical pointer binding before a separate pointer repair. |

Reachable configured pages are explicitly supplemental evidence. They are not
promoted to API-authorized replacement websites, and their address prose was not
used to infer corrections. Five old API website pointers have reachable
configured counterparts with SeatEngine markers (74, 441, 571, 637, 644), making
pointer obsolescence plausible but not independently established. All five
unavailable API identities also have reachable configured classic SeatEngine
pages; the website/API discrepancy needs investigation, not automatic retirement.

## Source 594: reproducible local cause

The API supplies `Http://www.deafpuppyclub.com`. The current
`URLUtils.normalize_url` helper prepends a scheme unless the input starts with
lowercase `http://` or `https://`, producing:

```text
Http://www.deafpuppyclub.com -> https://Http://www.deafpuppyclub.com
```

Both native fetch paths consequently try to resolve host `Http`. The controlled
input `http://www.deafpuppyclub.com` returns HTTP 200 and redirects to
`https://www.deafpuppyclub.com/`, with the Deaf Puppy title and classic SeatEngine
markers. The report retains both live attempts and the actual offline helper
result. The next code task should test mixed-case schemes in shared normalization
and then rerun the resolver. This audit makes no runtime or configuration change.

## Method and verification

- Read exactly the 15 source rows and their 15 clubs through a PostgreSQL
  read-only session. Save complete before-images privately; close the database
  connection before starting network requests.
- Use `core.clients.seatengine.geo.client_for` and authenticated
  `SeatEngineClient.fetch_venue_details` for exact configured classic IDs. Repeat
  unavailable identities. Retain the native HTTP status and sanitized response
  body (including HTTP 200 with null data), rather than treating None as a 404.
- Fetch API-listed websites through the scraper's native curl-cffi/Playwright
  stack with explicit accept-only headers; never forward the SeatEngine token.
  Curl network failures that prevent automatic fallback receive a direct native
  Playwright attempt. Retain certificate verification.
- Bound each operation to 90 seconds, separately for API and website, with two
  concurrent sources on one event loop. The earlier audit had a combined
  25-second deadline; these results identify concrete failures rather than
  attributing them to that deadline.
- Repeat the probes outside the sandbox to distinguish real DNS failures from
  sandbox network restrictions. The committed detailed attempts are that
  recheck. Supplemental source URLs are labeled as configured, unverified
  pointers, including any scheme added to an initially schemeless source URL.
- Capture only status, URL, response hashes, public identity fields, and bounded
  sanitized excerpts. Native curl status/final URL is distinguished from browser
  outcomes. No credentials, private full snapshots, or authentication headers are
  included. Scratch probe paths and hashes are recorded for local traceability.
- Compare complete source and club rows after the network work, then perform an
  independent fresh read-only comparison. Both match the original snapshot:
  `a6163ce9941974bb5e2568b1015999a95f0ac577f07b7c470603db08aa498921`.
  Validate the exact 15-source set, per-operation URLs/timestamps, every available
  API website's attempted fetch, and absence of configured secrets in the report.

No scrape persistence, enrichment, geographic updates, source mutations,
configuration repairs, or resolver expansion occurred. Repairs and any broader
platform investigation require separately scoped work using these next actions.
