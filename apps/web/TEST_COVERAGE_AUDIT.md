# Web Test Coverage Audit — 2026-05-20

Source: `npx vitest run --coverage` (v8 instrumentation) against
`apps/web` on commit `86c02ee2` (main).

## Headline numbers

| metric     | covered / total | pct      |
| ---------- | --------------- | -------- |
| statements | 4096 / 4967     | 82.46%   |
| branches   | 2602 / 3677     | 70.76%   |
| functions  |  934 / 1145    | 81.57%   |
| lines      | 3865 / 4598     | 84.05%   |

Test files: 358. The numbers above only count files that were
**imported by at least one test**.

## The headline is misleading

Vitest's v8 coverage only instruments files reached during a run. Files
that no test imports are absent from the report — they look like "0%" but
don't drag the totals down. Reality:

- **252 of 456 source files (55%)** in `apps/web` are never imported by
  any test. They are effectively uncovered, but invisible in the 84%
  number.
- The "well-tested" headline is driven by `ui/components/*` (which has
  dense `*.test.tsx` siblings) and the API route layer
  (`app/api/**/route.ts` — 38 of 44 routes covered at ≥80%).
- The gap is concentrated in the server-only path: NextAuth config,
  server actions, detail-page data orchestrators, and a handful of
  public API routes.

## Top 10 most undertested critical paths

Ranked by **likely user impact × untested LOC**.

| # | path | lines | line cov | branch cov | notes |
| - | ---- | ----- | -------- | ---------- | ----- |
| 1 | `auth.ts` | 172 | **0%** | n/a | NextAuth `session`, `jwt`, `signIn` callbacks + magic-link transport. A break silently logs the wrong user out or shapes the wrong profile into the session. |
| 2 | `lib/data/comedian/detail/getComedianHeroPalette.ts` | 139 | **0%** | n/a | Heaviest unsubstituted logic in the comedian detail page (image-color extraction, fallbacks). Drives the most-trafficked SEO surface. |
| 3 | `lib/data/comedian/detail/findRelatedComedians.ts` | 105 | **0%** | n/a | Co-bill / "related comedians" query. Powers the cross-link graph on every comedian page. |
| 4 | `app/api/unsubscribe/route.ts` | 95 | **0%** | n/a | Email unsubscribe handler. Compliance-relevant — silent breakage means user complaints and CAN-SPAM exposure. |
| 5 | `lib/data/club/detail/findClubByName.tsx` | 89 | **0%** | n/a | The lookup that resolves `/club/[name]` → club row. Untested includes slug-matching fallbacks. |
| 6 | `lib/data/profile/updateUserProfileData.ts` (75) + `getUserProfileData.ts` (64) | 139 | **0%** | n/a | Every logged-in user's profile read/write. Branches include zip-code parsing and notification opt-ins. |
| 7 | `middleware.ts` | 75 | 62.7% | **50%** | Auth-gated redirect logic. Branch coverage is half; the untested branches are precisely the redirect cases (no session → login, expired token, etc.). |
| 8 | `lib/data/show/detail/getShowDetailPageData.ts` (11) + `lib/data/club/detail/getClubDetailPageData.tsx` (57) + `getComedianDetailPageData.tsx` (44) | 112 | **0%** | n/a | The three detail-page orchestrators. They wrap individually-tested `findX` helpers, but the orchestration (cache keys, fallbacks, parallel fetches) is unverified. |
| 9 | `app/actions/favorite.ts` | 45 | **0%** | n/a | Server action behind `useFavorite`. The Zod-validation and `session.profile` guard branches are untested, even though `toggleFavorite` (the underlying mutation) is 100%. |
| 10 | `lib/data/filters/getFilters.ts` (55) + `getChainFilters.ts` (37) + `lib/data/club/search/findClubsWithCount.tsx` (117) | 209 | **0%** | n/a | Search/discovery query builders. Heavy, branchy, never invoked by a unit test. |

Other 0% spots worth knowing about but not in the top 10:

- `lib/auth/resolveAuth.ts` (61, 0%) — auth resolution helper.
- `app/api/v1/podcasts/search/route.ts` (32, 0%) + `app/api/v1/zip-lookup/route.ts` (35, 0%) — public API routes with no test.
- `lib/data/stats/getStats.ts` (62, 0%) — homepage stats card.
- `app/actions/resolveLocationAction.ts` (23, 0%) + `getComediansByZipAction.ts` (14, 0%) — geo actions.

## Pre-launch vs post-launch decisions

The "launch" assumption here is the in-progress iOS App Store submission
(see TASK-2349, TASK-2355, TASK-2357 on `main`). Webcorrectness already
gates production via Vercel; what we want to bias toward is **breakage
that would be invisible until a user complains.**

### Pre-launch additions (file as follow-up tasks)

1. **`auth.ts` callbacks** — unit-test `session`, `jwt`, and `signIn`
   callbacks. Mock `prisma.userProfile.findUnique`; assert the session
   shape with/without a profile row, and that `jwt({ trigger: "update" })`
   refreshes the profile. **Why pre-launch:** an iOS-app session
   regression breaks every login, and there is currently zero defense.
2. **`middleware.ts` auth branches** — bring branch coverage from 50% to
   ≥80% by adding fixtures for: (a) no session on a gated route, (b)
   expired JWT, (c) public route while authenticated. **Why pre-launch:**
   redirect logic is silent when it breaks — failure mode is "logged-out
   user sees blank page."
3. **`app/actions/favorite.ts`** — test the Zod validation branch, the
   "no session" branch, and the "no profile" branch. The success path
   already exercises `toggleFavorite`. **Why pre-launch:** favoriting is
   the primary engagement mechanic. Server-action errors surface to the
   iOS app as opaque 500s.

### Post-launch hardening (defer)

4. **Detail-page data orchestrators** (`getClubDetailPageData`,
   `getComedianDetailPageData`, `getShowDetailPageData`) — wrap helpers
   that are individually tested. Integration tests would catch
   cache-key / parallel-fetch regressions, but the underlying queries
   are sound. Defer.
5. **`getComedianHeroPalette.ts`** — 139 lines of image-color extraction
   with fallbacks. High LOC but the failure mode is visual (a grey hero
   instead of a coloured one), not data corruption. Defer to a visual
   regression suite.
6. **`findRelatedComedians.ts`** — co-bill query. Defer; broken
   "related" lists degrade discovery but don't break the core flow.
7. **Profile read/write data fetchers** — only a small slice of users
   edit their profile in a given week. Defer.
8. **Search query builders** (`findClubsWithCount`, `getFilters`,
   `getChainFilters`) — covered indirectly by collection-page UI
   tests. Defer.
9. **Unsubscribe route** — compliance-relevant but very low traffic and
   easy to detect via email complaints. Defer with an alert on its
   error rate instead.
10. **Public API routes without tests** (`/api/v1/podcasts/search`,
    `/api/v1/zip-lookup`) — low blast radius; defer.

### Don't do at all

- Coverage gates in CI right now. The 84%/55% gap above shows that a
  threshold gate would be lying. Get the pre-launch additions in
  first, then revisit whether a real gate makes sense once the picture
  isn't dominated by the invisible-files problem.

## How to reproduce

```bash
cd apps/web
npx vitest run --coverage \
  --coverage.reporter=json-summary \
  --coverage.reporter=text-summary \
  --coverage.reporter=text
```

`@vitest/coverage-v8` is now a devDependency. Coverage output lands in
`apps/web/coverage/` (gitignored).
