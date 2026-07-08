# Detail Cache User Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split detail page cache reads from per-user favorite markers so authenticated traffic can share anonymous cache entries.

**Architecture:** Detail pages will call anonymous cached fetchers keyed by slug/timezone plus whitelisted output-affecting params. Small per-user overlay helpers will run outside `unstable_cache` and patch favorite flags on returned DTOs without changing the anonymous payload shape.

**Tech Stack:** Next.js App Router Server Components, `unstable_cache`, Prisma, Vitest.

---

### Task 1: Cache Key And Overlay Helpers

**Files:**
- Create: `apps/web/lib/data/detail/personalizedOverlay.ts`
- Test: `apps/web/lib/data/detail/personalizedOverlay.test.ts`

- [ ] Write tests for whitelisted cache keys and favorite overlay patching.
- [ ] Run: `cd apps/web && npm test -- lib/data/detail/personalizedOverlay.test.ts`
- [ ] Implement `buildDetailCacheKey`, `applyFavoriteOverlay`, and `isPodcastFavorite`.
- [ ] Re-run the focused test until it passes.

### Task 2: Detail Page Orchestrators

**Files:**
- Modify: `apps/web/app/(entities)/(detail)/club/[name]/page.tsx`
- Modify: `apps/web/app/(entities)/(detail)/comedian/[name]/page.tsx`
- Modify: `apps/web/app/(entities)/(detail)/podcast/[slug]/page.tsx`
- Inspect: `apps/web/app/(entities)/(detail)/show/[id]/page.tsx`

- [ ] Use anonymous request data in club and comedian `unstable_cache`.
- [ ] Replace raw `JSON.stringify(requestData)` cache keys with `buildDetailCacheKey`.
- [ ] Keep coarse detail revalidation tags present.
- [ ] Apply favorite overlays outside cache for club/comedian show lineups and comedian detail header.
- [ ] Fetch podcast detail anonymously, then patch `podcast.isFavorite` outside cache.

### Task 3: Verification

**Files:**
- Existing focused tests under `apps/web/lib/data/detail/`

- [ ] Run the focused helper test.
- [ ] Run `grep -rq "club-detail-data" apps/web/app`.
- [ ] Run a targeted type check if the focused test passes.
