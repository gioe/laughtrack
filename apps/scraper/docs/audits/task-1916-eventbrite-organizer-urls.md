# TASK-1916 — Eventbrite Organizer-URL Audit (2026-05-04)

Pre-flight audit ahead of the first nightly run (2026-05-05 06:00 UTC) under
TASK-1891's organizer-mode routing in `EventbriteScraper.scrape_async`. Any
`source_url` containing `/o/` now bypasses the single-venue transformer pipeline
and instead groups events by `api_venue.id`, calling `upsert_for_eventbrite_venue`
per distinct venue.

22 clubs have an eventbrite `scraping_sources` row whose `source_url` contains
`/o/`. Each was probed by fetching the organizer feed via `EventbriteClient.fetch_all_events`
and grouping events by venue; the venue group names were then deduped against
the existing club name to predict whether shows will stay attached or reroute
to a newly-created per-venue club row.

The grouping-by-`venue.id` count alone is misleading: Eventbrite organizer
feeds frequently emit a fresh `venue.id` per show occurrence even when the
physical venue is unchanged. What matters at flip time is whether the venue
**name** matches the existing club name (UPSERT_CLUB_BY_EVENTBRITE_VENUE keys
on `clubs.name` ON CONFLICT), so events with venue.name == clubs.name collapse
back onto the existing club regardless of how many distinct venue ids appear.

## Classification

| club_id | club_name | events | unique venue names | events_stay | events_reroute | classification | follow-up |
|--------:|-----------|-------:|-------------------:|------------:|---------------:|----------------|-----------|
| 181 | The Lincoln Lodge | 466 | 1 | 466 | 0 | SAFE | none |
| 162 | Westside Comedy Theater | 219 | 1 | 219 | 0 | SAFE | none |
| 153 | Next In Line Comedy | 182 | 1 | 182 | 0 | SAFE | none |
| 168 | Laugh Factory Chicago | 109 | 1 | 109 | 0 | SAFE | none |
| 575 | The Attic Comedy Club | 86 | 1 | 86 | 0 | SAFE | none |
| 21 | Comic Strip Live | 39 | 1 | 39 | 0 | SAFE | none |
| 452 | The Nut House Comedy Lounge | 4 | 1 | 4 | 0 | SAFE | none |
| 646 | The Comedy Inn | 4 | 1 | 4 | 0 | SAFE | none |
| 654 | Big Couch New Orleans | 134 | 2 | 44 | 90 | PARTIAL | sibling task |
| 160 | Laugh Factory Hollywood | 165 | 1 | 0 | 165 | REROUTED | sibling task |
| 184 | The Comedy Bar Chicago | 106 | 1 | 0 | 106 | REROUTED | sibling task |
| 169 | Laugh Factory Long Beach | 89 | 1 | 0 | 89 | REROUTED | sibling task |
| 199 | The Riot Comedy Club | 66 | 2 | 0 | 66 | REROUTED | sibling task |
| 647 | Backdoor Comedy Club | 56 | 1 | 0 | 56 | REROUTED | sibling task |
| 170 | Laugh Factory San Diego | 50 | 1 | 0 | 50 | REROUTED | sibling task |
| 1052 | Comedy At The Comet | 29 | 4 | 0 | 29 | REROUTED | sibling task |
| 1038 | Counter Weight Brewing | 1 | 1 | 0 | 1 | REROUTED | sibling task |
| 1136 | Lake Theater & Cafe | 1 | 1 | 0 | 1 | REROUTED | sibling task |
| 809 | Improbable Comedy | 4 | 2 | 0 | 4 | REROUTED | TASK-1914 (covered) |
| 190 | CIC Theater | 0 | 0 | 0 | 0 | EMPTY (already disabled) | none |
| 200 | Comedy on Collins | 0 | 0 | 0 | 0 | EMPTY | sibling task |
| 510 | Comedy Blvd | 0 | 0 | 0 | 0 | EMPTY | sibling task |

**Totals:** 8 SAFE / 1 PARTIAL / 10 REROUTED / 3 EMPTY (1 already disabled).

No name collision was detected against any *other* existing `clubs` row for the
14 distinct rerouted venue-name spellings — meaning the new per-venue rows
will be greenfield inserts, not silent merges into unrelated clubs.

## Per-Club Detail (REROUTED + PARTIAL)

### club 654 — Big Couch New Orleans (PARTIAL, 134 events)
- 90 events under venue.name `'Big Couch'` (will create new club row)
- 44 events under venue.name `'Big Couch New Orleans'` (matches existing club)
- Same physical venue; the organizer feed inconsistently spells the name.
- Recommended disposition: investigate whether to rename club 654 to `'Big Couch'`, or repoint to a venue-mode URL.

### club 160 — Laugh Factory Hollywood (REROUTED, 165 events)
- 165 events under venue.name `'Laugh Factory - Hollywood'` (note hyphen).
- Recommended disposition: repoint `source_url` to the venue-mode URL for this Eventbrite venue id.

### club 184 — The Comedy Bar Chicago (REROUTED, 106 events)
- 106 events under venue.name `'The Comedy Bar - Chicago Main Stage'`.
- Recommended disposition: repoint to venue-mode URL.

### club 169 — Laugh Factory Long Beach (REROUTED, 89 events)
- 89 events under venue.name `'Long Beach Laugh Factory'` (word order swapped).
- Recommended disposition: repoint to venue-mode URL.

### club 199 — The Riot Comedy Club (REROUTED, 66 events)
- 41 events under venue.name `"Rudyard's"` and 25 under `"The Riot Comedy Club upstairs at Rudyard's"`.
- Same physical venue (Rudyard's, Houston TX) but two distinct names.
- Recommended disposition: repoint to venue-mode URL for whichever Eventbrite venue id has the canonical spelling, or rename the existing club to `"Rudyard's"`.

### club 647 — Backdoor Comedy Club (REROUTED, 56 events)
- 56 events under venue.name `'Backdoor Comedy'` (suffix dropped).
- Recommended disposition: rename existing club to `'Backdoor Comedy'`, or repoint to venue-mode URL.

### club 170 — Laugh Factory San Diego (REROUTED, 50 events)
- 50 events under venue.name `'Laugh Factory'` (no city qualifier — collides conceptually with other Laugh Factory clubs).
- Recommended disposition: repoint to venue-mode URL — name-only UPSERT would fold San Diego shows into a generic `'Laugh Factory'` row that other LF organizers could land on.

### club 1052 — Comedy At The Comet (REROUTED, 29 events)
- 16 events `'Bombs Away! Comedy at the Comet'`, 6 `'Bombs Away Comedy'`, 4 `'Mellotone Beer Project'`, 3 `'The Comet'`.
- This organizer is genuinely multi-venue (Bombs Away brand running shows at The Comet AND Mellotone Beer Project).
- Recommended disposition: investigate. Likely repoint to venue-mode URL for The Comet, hide brand club, or split into per-venue clubs.

### club 1038 — Counter Weight Brewing (REROUTED, 1 event)
- 1 event under venue.name `'Counter Weight Brewing Company'`.
- Recommended disposition: rename existing club to add `' Company'` suffix, or repoint to venue-mode URL.

### club 1136 — Lake Theater & Cafe (REROUTED, 1 event)
- 1 event under venue.name `'The Fonda Theatre'` (Los Angeles, CA — different city + state from existing club in Lake Oswego, OR).
- This organizer URL is wrong — does not actually represent Lake Theater & Cafe.
- Recommended disposition: disable this `scraping_sources` row; the URL is misattributed.

### club 809 — Improbable Comedy
- Already covered by TASK-1914.

## Per-Club Detail (EMPTY)

### club 190 — CIC Theater (EMPTY)
- `scraping_sources.enabled = FALSE` already; organizer-mode flip has no effect.
- No action needed.

### club 200 — Comedy on Collins (EMPTY)
- Organizer feed returns 0 events; `scraping_sources.enabled = TRUE`.
- Recommended disposition: investigate whether organizer is dormant or URL is stale.

### club 510 — Comedy Blvd (EMPTY)
- Organizer feed returns 0 events; `scraping_sources.enabled = TRUE`.
- Recommended disposition: investigate whether organizer is dormant or URL is stale.

## Reproducing the Audit

The probe is pure-read against the Eventbrite API; no DB writes. Re-run with:

```bash
cd apps/scraper && .venv/bin/python3 /tmp/audit_organizer_urls.py
```

The script (kept under `/tmp/audit_organizer_urls.py` during this session,
not committed — it's a one-shot probe) iterates `scraping_sources` rows
where `platform='eventbrite'` and `source_url LIKE '%/o/%'`, instantiates
an `EventbriteClient` per club, and groups `fetch_all_events()` results
by venue name. The classification logic is documented inline above.

## Spot-Check Plan (criterion 3)

After the 2026-05-05 06:00 UTC nightly:

1. Pull the Discord #laughtrack scraper-summary message for the run.
2. Compare per-club show counts at the SAFE clubs against the pre-flip 2026-05-04 23:30 UTC baseline (Lincoln Lodge 601→~466 expected, etc. — note that the organizer feed only returns *upcoming* events, so a drop from the baseline to roughly the audit's `events` column for each SAFE club indicates the new path produced what was predicted).
3. Confirm no SAFE club lost 100% of its shows (which would indicate the name-match prediction was wrong).
