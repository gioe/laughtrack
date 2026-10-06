# SeatEngine geographic audit — TASK-4114

Run on 2026-10-05 EDT (2026-10-06 UTC). All **133 enabled sources** with
SeatEngine platform or ID fields were included, including one hidden club.
The cohort contains 105 distinct classic venue IDs. See [results.json](results.json)
for every source, its evidence URLs, outcome, and unresolved reason.

| Outcome | Sources |
| --- | ---: |
| Structured city/state matches | 1 |
| Confirmed city/state mismatches | 0 |
| Missing supported metadata | 89 |
| Fetch/API failures | 15 |
| Missing classic venue ID | 26 |
| Unsupported v3-only ID | 2 |

**This is not a clean bill of geographic health:** only one source supplied
the supported, unambiguous venue-level evidence. The other 132 remain unresolved.
There were no capped resolutions or conflicting structured metadata in this run.

## Evidence and interpretation

Classic venue API responses identify a venue and its website but do not expose
structured addresses. The resolver verifies the returned numeric ID, fetches only
the API-listed website through the scraper HTTP stack, and accepts venue-level
EventVenue JSON-LD whose URL and name agree with that identity. Website paths
remain significant; names are used for identity agreement, never geographic
inference. Event locations, biographies, descriptions, and search results are
not accepted as venue identity. Multiple or conflicting addresses stay unresolved.
Postal disagreements are retained as warnings without selecting a corrected ZIP.

Source **591**, club **1347**, classic venue **650** (Whiplash Comedy):

- API: `https://services.seatengine.com/api/v1/venues/650`
- API-listed site: `https://whiplashcomedy.com/`
- Structured venue URL: `https://www.whiplashcomedy.com`
- Current structured address: **650 North Avenue Suite S201, Atlanta, GA 30308**.
- Current club city/state/ZIP: **Atlanta, GA 30308** — matches.

The [September 29 evidence](../2026-09-29-whiplash/source-evidence.json)
recorded Atlanta/GA with ZIP 30080 and Suite S210. The official site has changed
since then. The historical Brooklyn/NY corruption and contradictory ZIP remain
regression fixtures; neither stale address nor a guessed correction was written
back. Street/suite changes are evidence only: this detector compares city/state
and reports postal differences, not street or coordinate repairs.

## Actionable review queues

1. **Five unavailable API identities:** sources 246, 631, 371, 431, 598. Check
   configured classic IDs and platform migration status before attempting geo
   reconciliation. These responses do not establish where the venue is.
2. **Ten unavailable API-listed websites:** sources 77, 134, 74, 644, 637, 268,
   441, 594, 82, 571. Verify the authoritative website or platform configuration;
   do not substitute the club's existing website merely because fetching failed.
3. **Ten API responses without an authorized website** and **79 fetched pages
   without supported EventVenue metadata:** inspect the per-source evidence in
   the JSON. A future resolver may add another structured format only after
   establishing venue-specific binding and ambiguity checks.
4. **26 missing IDs and two v3-only sources:** resolve the missing configuration
   or implement an independently verified v3 identity/address path. No classic
   IDs or geographic values were inferred from names or URLs.

These are review queues, not confirmed geographic errors or approved repairs.
No new tasks or venue modifications were made as part of this audit.

## Reproduction and safety

From `apps/scraper/`, with the usual `.env` credentials:

```sh
PYTHONPATH=src:. .venv/bin/python3 bin/audit-club-source-geo \
  --signal source_venue_geo_mismatch --platform seatengine \
  --enabled-only --include-hidden --format json
```

Database access uses a read-only session and closes before network resolution.
Website fetches explicitly exclude the SeatEngine API credential. Resolution is
bounded to four concurrent venues, with a 25-second deadline per venue; failures
and resolution caps remain visible per source. Default offline audit behavior
does not initiate these network calls.

Before/after read-only cohort snapshots were identical across source IDs,
platform configuration, club names, address/city/state/ZIP, coordinates, Google
place IDs, websites, and visibility. The report has exactly the same 133 source
IDs as both snapshots. The canonical snapshot SHA-256 is stored in results.json.
No venue writes, migrations, enrichment jobs, or scraper persistence ran.
