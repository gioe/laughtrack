# LaughTrack — Project Conventions

Detailed conventions live in the **tusk conventions database**, not inline in this file.
Loading every rule on every conversation wastes context budget on rules that don't
apply to the file you're touching. Conventions are keyed by topic tags so they can
be loaded on demand.

## Discover relevant rules

```bash
tusk conventions inject <path>      # auto-match conventions by file path heuristics
tusk conventions search <term>      # full-text search across body and topics
tusk conventions list --topic <tag> # filter by tag (e.g. prisma, vitest, scraper)
tusk conventions list               # full list, grouped by topic
```

Run `tusk conventions inject <path>` before editing in an unfamiliar area —
it surfaces gotchas, workarounds, and invariants you would otherwise hit the hard way.

## Common topic tags

- **Scraper**: `scraper`, `scraper-chains`, `eventbrite`, `playwright`, `seatengine`,
  `scraping_sources`, `tixr`
- **Prisma / DB**: `prisma`, `migrations`, `neon`, `transactions`, `sql`
- **Frontend**: `frontend`, `nextjs`, `react`, `ssr`, `middleware`, `tailwind`,
  `dev-server`, `routes`, `rate-limit`
- **Testing**: `vitest`, `pytest`, `mocking`, `sys.modules`, `auth`, `happy-dom`
- **Tooling**: `tusk`, `git`, `bash`, `makefile`, `paths`

## Cross-reference files

- `apps/scraper/SCRAPERS.md` — platform-specific venue onboarding guides
  (StageTime, Prekindle, Humanitix, Tixr, Eventbrite, SeatEngine, Squarespace,
  Tockify, OvationTix, OpenDate, TicketSource, etc.)
- `apps/scraper/CONTRIBUTING.md` — scraper testing patterns (smoke tests, module
  loading, mocking, async, VCR cassettes)

## Adding new conventions

When you learn a non-obvious rule about this codebase — a gotcha, workaround,
invariant, or an incident's root cause — capture it as a tusk convention with
topic tags rather than appending to this file:

```bash
tusk conventions add --topics "tag1,tag2,tag3" "Short, action-oriented rule. \
Why it matters. How to apply it."
```

Use multi-line text for code examples. The body can include fenced code blocks.

## Scraper Configuration Model — quick reminder

Per-platform scrape configuration belongs in `scraping_sources` (keyed by
`(club_id, platform, priority)`), not on `clubs`. Treat `clubs` as venue identity
only. When onboarding or switching a venue, insert/update the appropriate
`scraping_sources` row — do not add new flat scraper config columns to `clubs`.
Run `tusk conventions search scraping_sources` for the full column reference.
