# Scraper Architecture Patterns

## Tixr Webflow Day-Card Config Wrappers

Decision for TASK-2071: do not fold the current Tixr Webflow day-card venues into
a metadata-driven generic scraper key yet.

This pattern applies when a venue-owned Webflow page renders complete show data
in `a.day-card` elements and the card links point to a venue-specific Tixr group
URL. The shared parser lives in
`apps/scraper/src/laughtrack/scrapers/implementations/api/tixr/webflow_day_card.py`.
Venue scrapers should stay as thin wrappers that provide:

- `default_source_url`
- `WebflowDayCardConfig(tixr_group_fragment=...)`
- `WebflowDayCardTransformer`
- `collect_scraping_targets()` returning the source URL
- `get_data()` fetching the page and calling `WebflowDayCardExtractor.extract_events(...)`

Current exact matches:

- `comic_strip_edmonton`
- `house_of_comedy_bc`

`haha_comedy_club` is not part of this pattern. It uses custom JSON-LD calendar
parsing plus visible time markup, because its linked Tixr event pages have been
blocked by DataDome and its page shape is not the shared `a.day-card` structure.

Keep the wrapper pattern as canonical for the next venue that exactly matches
the same Webflow/Tixr group-card shape. Consider folding into a metadata-driven
generic key only after a fourth exact match appears, or if a future onboarding
requires no code beyond the same two config fields:

- `source_url`
- `tixr_group_fragment`

Until then, the wrappers are easier to discover through scraper registration,
cheaper to debug, and avoid runtime indirection through `scraping_sources.metadata`
for a pattern that currently covers only two venues.
