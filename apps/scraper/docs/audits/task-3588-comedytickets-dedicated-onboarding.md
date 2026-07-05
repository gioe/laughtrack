# TASK-3588 ComedyTickets dedicated-club onboarding

Input: `apps/scraper/docs/audits/task-3587-comedytickets-source-triage.csv`, filtered to `next_task=3588`.

ComedyTickets remains a discovery signal only. No ComedyTickets URL is used as a route target or scraping source.

## Outcome

- Total dedicated-candidate rows reviewed: 47.
- Already covered by an enabled first-party/source row in production: 21.
- Newly staged for onboarding in this task: 2.
- Left without an enabled source pending venue-specific research: 24.
- CSV disposition report: `apps/scraper/docs/audits/task-3588-comedytickets-dedicated-onboarding.csv`.
- Migration: `apps/web/prisma/migrations/20260705200000_onboard_comedytickets_dedicated_verified_sources/migration.sql`.

## Staged Onboarding

| Candidate | First-party verification | Scraper config | Smoke result |
|---|---|---|---|
| Funny Bone Comedy Club - St. Louis | `https://stlouisfunnybone.com/events` exposes StandUp Media frontend config: `clubid=718bd264-309b-4fa0-a6fa-0b93455f88d0`, `dbname=stlouis_prod`. | `platform=custom`, `scraper_key=standup_media`, source URL `https://stlouisfunnybone.com/events`, metadata `standup_media_location_id` + `standup_media_dbname`. | `StandUpMediaScraper` returned 113 future shows. |
| Hyena's Comedy Nightclub Fort Worth | `https://hyenascomedynightclub.com/fort-worth` links to `https://www.prekindle.com/events/hyenasfortworth`; that Prekindle page carries JSON-LD comedy events. | `platform=custom`, `scraper_key=json_ld`, source URL `https://www.prekindle.com/events/hyenasfortworth`. | `JsonLdScraper` returned 90 future shows. |

## Duplicate Guard

The migration inserts a club only when neither of these exists:

- Exact `clubs.name` match.
- Same normalized first street-address segment.

It inserts a `scraping_sources` row only when the resolved club has no enabled source. This prevents duplicate records for existing clubs and avoids creating a second enabled priority-0 source.

## Not Enabled In This Pass

Rows left as `needs_manual_research` were not enabled because the pass did not produce a verified first-party source that could be smoke-tested with an existing scraper, or because automatic DB name matches were low-confidence different venues.

Examples:

- `Dallas Comedy Club` matched unrelated Dallas venues by name token only.
- `Greenwich Village Comedy Club` matched other NYC/MacDougal clubs, not a confirmed canonical row.
- `Hyena's Comedy Night Club - Albuquerque` has a first-party page, but tested Prekindle slugs did not expose future JSON-LD events in the scraper probe.
- `Loony Bin Comedy Club - Tulsa` matched Tulsa Theater and a hidden closed Tulsa Comedy Club row, neither suitable for enabling.
- `San Antonio Improv` needs a first-party identity decision separate from LOL San Antonio before adding a source.

## Verification Commands

Smoke probes were run with the scraper stack against in-memory `Club` / `ScrapingSource` objects:

```bash
cd apps/scraper && .venv/bin/python3 - <<'PY'
# Instantiated StandUpMediaScraper and JsonLdScraper with verified source configs.
PY
```

Playwright first-party fetchability probes had to run outside the sandbox because Chromium failed to launch in the sandbox with `MachPortRendezvousServer permission denied`.
