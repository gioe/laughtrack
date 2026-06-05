# Home Page Fixture Verification

Use fixture mode for manual home-page carousel checks that should not depend on
production Neon latency or live event inventory:

```bash
cd apps/web
E2E_FIXTURE_MODE=1 npm run dev
```

Then open `/`. Fixture mode renders deterministic `Shows Tonight`,
`Nearby Shows`, and `Trending This Week` carousels with stable `data-testid`
values from `lib/data/home/homeFixtures.ts`.

## Timing Notes

TASK-2667 measured the local Next dev home page with New Rochelle geo headers
against production Neon:

- Cold request: `GET /` returned 200 in 24.6s. Server logs showed 16.3s spent
  compiling `/`, while home-page data fetches completed before render in 4.2s.
- Warm request: `GET /` returned 200 in 4.6s. Data fetches completed before
  render in 2.4s.
- Warm section timings: `getCachedHomePageData` 181ms,
  `getComediansByZip` 371ms, `getTrendingShowsThisWeek` 496ms,
  `getShowsNearZip` 599ms, `getShowsTonight` 635ms.

The slow manual-verification path is therefore dominated by cold Next dev
compilation and local environment variance, not a single obviously slow home
data query. Use fixture mode when verifying carousel layout or copy.
