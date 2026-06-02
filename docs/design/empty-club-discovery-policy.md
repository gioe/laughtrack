# Empty-Club Discovery Policy

## Context

After `TourDatesScraper` was deleted in TASK-2581, ~74 clubs whose only
upcoming-show inventory came from BandsInTown/tour_dates ingestion have zero
upcoming shows. Their `Club` rows remain `status='active'` and `visible=true`
— only their show pipeline is dormant — so they would otherwise still surface
in discovery surfaces with no actual content behind them.

The UI already has two relevant invariants:

- "Tickets are access records, not purchase rows": every legitimate show emits
  at least one ticket, so the absence of tickets means the show is genuinely
  absent — not that it's free/RSVP-only. (See `MEMORY.md`.)
- "Weak signal hidden by default": the club search FilterBar comment
  (`apps/web/ui/pages/search/filterBar/index.tsx`) already states "by default
  hides results with weak signal: clubs/comedians with no upcoming shows".

This doc captures how dormant clubs should appear across discovery surfaces.

## Decision: Hybrid — hide from discovery, keep detail page reachable

Empty clubs are **excluded from discovery surfaces** (club search results,
home page "Trending Clubs" carousel, iOS `/api/v1/clubs`, iOS
`/api/v1/home/feed`). They remain **fully reachable** at `/club/[name]`
direct URLs.

### What this means on each surface

| Surface | Behavior | Where it's enforced |
| --- | --- | --- |
| Club search (`/club/search`) | Hidden by default. Opt-in toggle (`includeEmpty=true`, the "Include all" checkbox in FilterBar) still surfaces them. | `apps/web/lib/data/club/search/findClubsWithCount.tsx` (already in place) |
| Home page "Trending Clubs" carousel | Hidden. | `apps/web/lib/data/home/getClubs.ts` (added in TASK-2585) |
| iOS `/api/v1/clubs` | Hidden — same `getClubs` fetcher. | same |
| iOS `/api/v1/home/feed` (`popularClubs`) | Hidden — same `getClubs` fetcher. | same |
| Club detail page `/club/[name]` | Renders cleanly with zero shows. Header + chain badge + sibling list render normally; the shows tab shows the existing `EmptyState` "No Shows Found". | `apps/web/ui/pages/search/table/index.tsx` (already in place) |
| Sibling clubs on a chain page | Unchanged — a chain location with zero shows is still contextually relevant when listing siblings of its chain. | `apps/web/lib/data/club/detail/findSiblingClubs.ts` |

## Why hybrid (rejected alternatives)

- **Hide entirely (also block detail URLs)**: would break SEO, deep links,
  and bookmarks. The 74 clubs are dormant, not deleted — their detail pages
  should still return 200, both because Google has them indexed and because
  an operator landing on a club page is the obvious cue to onboard a
  replacement scraper.
- **Show everywhere with a placeholder card**: surfacing dormant venues in
  discovery dilutes signal. The codebase already articulated this policy in
  the FilterBar comment ("weak signal"); the search default has filtered
  empty clubs out for a long time. The home carousel and iOS feeds were
  inconsistent — fixing that inconsistency is the actual scope of TASK-2585.

## Reversibility

Two opt-outs already exist:

- **End users**: the `includeEmpty=true` URL param + "Include all" toggle on
  `/club/search` shows every active club regardless of show presence.
- **Future code**: if any caller of `getClubs()` genuinely needs all clubs
  (e.g., an internal admin list), add an `includeEmpty?: boolean` option to
  `GetClubsOptions` and gate the `shows: { some: ... }` clause on it.
  Discovery is the only current consumer, so the option is omitted today.

## Onboarding empty clubs back into discovery

When a real scraper is onboarded for one of the 74 dormant clubs (per
`scraping_sources`), shows will start landing and the club will reappear in
all four discovery surfaces automatically — no UI/code change required. The
`shows: { some: { date: { gt: now } } }` predicate self-heals.
