# TASK-4068: Rozzie relocation review

Checked 2026-09-29. Club 10970 is The Rozzie Square Theater in Roslindale,
a Boston neighborhood. This is the same business after a physical move,
not an alternate entrance and not a second venue to insert.

## Authoritative evidence

- [Official relocation notice](https://www.rozziesquaretheater.com/relocation):
  moved temporarily from 5 Basile Street to 18 Corinth Street in March 2026
  during redevelopment of the former site.
- [Official about page](https://www.rozziesquaretheater.com/about): old site
  operated May 2018–March 2026; describes new location as 18b Corinth Street
  and anticipated return after redevelopment in fall 2027. Recheck then;
  do not schedule an automatic reversal based on a projected date.
- [Official parking directions](https://www.rozziesquaretheater.com/transportation-parking)
  and [calendar](https://www.rozziesquaretheater.com/calendar): 18 Corinth St,
  Roslindale/Boston, MA 02131.
- Google Places details for the EXISTING business ID
  ChIJRVOdn8x-44kRtXtU9mgi-jE and an independent text search both return
  that theater at 18 Corinth St, Roslindale, MA 02131, with coordinates
  42.286516, -71.13004409999999. Address components identify Boston as
  locality and Roslindale as neighborhood. See place-evidence.json.

Use canonical street address `18 Corinth St, Roslindale, MA 02131`, ZIP
`02131`, and the current business point. The 18b variant is documented
but not a competing physical site. Retain Boston, MA, America/New_York,
name, website, Google place ID, visibility, source ownership and all references.

## Current defect and provenance

Before: address 5 Basile St, Roslindale, MA 02131; ZIP null; coordinates
42.2869269, -71.1272674. The archived June 22 onboarding script copied the
old address and did not insert zip_code. Its comment describing the street
variants as shared-building entrances is contradicted by the official move
notice. The archive is not the recurring scraper and is left untouched.

Source 6820 remains enabled, platform custom, scraper_key anyroad,
plugin rozziesquaretheater, URL https://app.anyroad.com/i/plugin/rozziesquaretheater.
There is no deny-list match. The current place ID remains valid for this business.

## Show assignment review and limits

All 144 show rows are attached to the theater's own AnyRoad source; 58 are
upcoming at the audit cutoff. Stored room breakdown: 87 at 18b Corinth;
9 at 18 Corinth Street; 3 named theater/Corinth Street; 1 full Corinth postal
address; 40 blank; 4 explicitly at The Substation, 4228 Washington Street.
None carry 5 Basile in room. Blank rooms do not independently establish an
exact performance location. Preserve every show, ticket, lineup and link.

Offsite rows 3179506, 3558318, 3179544 and 3179545 are not evidence that the
venue itself belongs at The Substation. The last is a future Nov 5 local-time
Level 1B Improv Showcase. Track explicit offsite venue handling separately;
a blanket reassignment during this address repair would be unjustified.
The official competition page also documents offsite programming.

The live AnyRoad API returned HTTP 403 through curl-cffi; this local Python
venv lacks Playwright, so automatic browser fallback was unavailable. Do not
interpret this as proof the production scraper is broken or claim a fresh
full scrape succeeded. Official current venue pages, Google business details,
stored show locations and existing AnyRoad fixtures agree on the relocation.

Before snapshot contains all club/source fields and counts plus fingerprints
of every foreign-key reference to this club or its shows. No user rows are
included. Rollback and post-application verification accompany the migration.
