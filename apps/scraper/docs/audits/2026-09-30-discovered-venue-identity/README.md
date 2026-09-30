# Generic discovery venue identity — TASK-4077

Audit date: 2026-09-30. Production access was read-only. No historical rows
were repaired in this task.

## Confirmed defect and prevention

On real PostgreSQL, inserting `Orpheum Theatre` in Wichita, KS and then
Minneapolis, MN returned the same club ID before the fix. The generic SQL
unconditionally reused `ON CONFLICT (name)`; Ticketmaster's separate identity
guard did not protect this path.

The conflict update now requires either complete matching city/state or a
nonempty matching postal code without any conflicting known city/state.
Comparisons ignore surrounding whitespace and case. A timezone alone is not
identity evidence. Complete matching city/state remains authoritative even
if incoming postal metadata differs; verified stored ZIP preservation is
unchanged. Postal-only callers can continue to reuse verified identities.

Uncorroborated collisions return no row and callers skip the event. This
deliberately favors omission over assigning a show to another city. No
synthetic venue names are generated. A previously unseen name can still
create a metadata shell with incomplete geography, but that does not authorize
later name-only reuse. The database conflict predicate also covers competing
inserts, rather than relying on a race-prone application precheck.

The existing fuzzy/alias lookup is limited to the supplied city/state. It
cannot bypass this protection with a different-city candidate. Eventbrite and
Ticketmaster use separate upserts and were not changed.

## All generic callers

| Caller | Geographic evidence | Effect of unresolved identity |
| --- | --- | --- |
| `ticket_tailor/scraper.py` | ZIP only; timezone not used as proof | Skips the venue's event group |
| `next_stop_comedy/scraper.py` | Address, ZIP from event payload | Skips event |
| `api/pabst_axs/group_scraper.py` | Venue payload with known address | Skips event |
| `api/comedian_websites/scraper.py` (two calls) | JSON-LD or registered extractor city/state, sometimes ZIP | Returns false; metadata-only discovery |
| `api/comedian_websites/platform_extractors.py` | Bandsintown city/region and postal code | Returns false; metadata-only discovery |
| `scripts/core/discover_clubs_from_comedian_show_pages.py` | Location string, possibly partial | Skips venue; existing log labels all skips as junk |

Source paths above are beneath `apps/scraper/src/laughtrack/scrapers/implementations/`
except the explicit `scripts/` path. Search included `src/`, `scripts/`, and `web/`.
The metadata-only path has no persisted discovery provenance; existing shell
rows cannot reliably be attributed to a particular caller.

## Bounded production sample

The production inventory contained 2,219 `next_stop_comedy` shows at 704 clubs,
134 `ticket_tailor` shows at two clubs, and 14 `pabst_theater_group` shows at
four clubs. `pabst_axs` also had six shows at three clubs, but that per-venue
scraper is distinct from the generic group caller.

`sample.json` contains the exact selection query and 20 selected show/club
pairs: one latest event per venue, all six TicketTailor/Pabst group venues,
The Clubhouse, then the first 13 Next Stop clubs with missing city or state.
This is a risk-directed sample, not a random prevalence estimate or an
exhaustive audit. Live pages were fetched using the scraper's HttpClient stack.
`source-six.json` retains the six TicketTailor/Pabst source observations.

Results: **16 geographically corroborated, one confirmed cross-city assignment,
three unresolved by the current event extractor**. ZIP matches corroborate
postal-only/international rows; they do not establish global uniqueness or
street-level venue identity.

### Confirmed cross-city cohort — TASK-4124

- Show **7123739**, the only show currently attached to club **8828**.
- Stored venue: The Clubhouse, **1607 N Vermont Ave, Los Angeles, CA 90027**.
- Official source: <https://www.nextstopcomedy.com/events/the-clubhouse-2026-10-24-8-pm>.
- Live event venue: The Clubhouse, **377 Denton Ave., New Hyde Park, NY 11040**.
- New ingestion is blocked by the guard; existing show references still require
  the evidence-locked repair tracked in TASK-4124.

### Other observations

- All six TicketTailor/Pabst identities agree with source postal/address evidence.
- Ten other Next Stop records agree on postal identity despite incomplete city/state.
- Shows **3590840**, **3590855**, **5388826** returned HTML but no event from
  the current extractor. This is not proof of cancellation or cross-city error.
  Existing TASK-4121 covers unresolved Next Stop source inventory; TASK-4122
  covers newly canceled events. These records are added as context for triage.
- Separate confirmed cancellation: Pabst show **3092815** at Turner Hall Ballroom
  remains `is_cancelled=false` after a 2026-09-30 scrape, while the official
  [Zarna Garg event page](https://www.pabsttheatergroup.com/events/detail/zarna-garg-2026)
  explicitly says the October 4 performance is canceled. **TASK-4125** tracks
  ingestion prevention and a guarded historical repair.

## Verification

`test_discovered_venue_cross_city_name_collision` executes the production SQL
against connection-local temporary PostgreSQL tables. It covers differing
cities/states, matching postal codes with contradictory geography, null/empty/
whitespace evidence, repeated verified identities, unknown existing shells,
postal-only reuse, and preservation of the original venue metadata.
The focused club-handler and postal-preservation suites passed 217 tests.
