import { CACHE } from "@/util/constants/cacheConstants";

/**
 * HTTP `Cache-Control` policies for the `/api/v1` read handlers (consumed by
 * the web app, iOS, and Android). These routes bypass the page-level
 * `unstable_cache` layer and query Neon on every request, so without cache
 * headers every mobile foreground refresh and CDN miss wakes Postgres. The
 * helpers below add explicit, freshness-aware policies keyed to how each route
 * varies:
 *
 *  - `PUBLIC_READ_CACHE_CONTROL` — for reads whose response is a pure function
 *    of the URL (path + query) with NO per-user variance (club/comedian/show
 *    detail, list endpoints, zip lookup). Safe to store in Vercel's shared CDN,
 *    so `s-maxage` absorbs the Neon cost for a full hour while `max-age` gives
 *    iOS/Android URLCache and browsers a short private TTL for rapid refetches.
 *    `stale-while-revalidate` lets the CDN serve slightly-stale data while a
 *    background refresh runs so a cache expiry never blocks on a cold query.
 *
 *  - `PRIVATE_READ_CACHE_CONTROL` — for reads that OPTIONALLY personalize via
 *    `resolveAuth` (favorite markers, profile-scoped ordering). The body can
 *    differ per user, so it must NEVER enter a shared cache. `private` keeps it
 *    in the end-user's own cache only; a short `max-age` still absorbs rapid
 *    foreground refetches without a shared-cache cross-user leak. Mirrors the
 *    long-standing `home/feed` policy.
 *
 *  - `NO_STORE_CACHE_CONTROL` — for authenticated / user-scoped / mutating
 *    routes (favorites, me/*, admin). Explicitly opts out of every cache tier.
 *
 * The TTLs reuse the existing `CACHE` constants so the HTTP layer and the
 * page-level `unstable_cache` layer stay in lockstep.
 */

/** Short client-side TTL (seconds) — absorbs rapid iOS/Android foreground refetches. */
export const PUBLIC_READ_CLIENT_MAX_AGE = 60;

/** Shared-CDN TTL (seconds) — the lever that keeps Neon asleep. Reuses CACHE.detailPage (1h). */
export const PUBLIC_READ_SHARED_MAX_AGE = CACHE.detailPage;

/** Request header name that `readTimezoneHeader` reads; timezone-varying routes must Vary on it. */
export const TIMEZONE_HEADER = "X-Timezone";

/**
 * Shared-cacheable public read: browsers/mobile cache 1 min, the CDN caches 1h
 * and may serve stale for another hour while it revalidates in the background.
 */
export const PUBLIC_READ_CACHE_CONTROL = `public, max-age=${PUBLIC_READ_CLIENT_MAX_AGE}, s-maxage=${PUBLIC_READ_SHARED_MAX_AGE}, stale-while-revalidate=${PUBLIC_READ_SHARED_MAX_AGE}`;

/** Private (per-client only) read — never enters a shared cache. */
export const PRIVATE_READ_CACHE_CONTROL = `private, max-age=${PUBLIC_READ_CLIENT_MAX_AGE}`;

/** Authenticated / user-scoped / mutating route — opt out of every cache tier. */
export const NO_STORE_CACHE_CONTROL = "private, no-store";

/**
 * Header object for a shared-cacheable public read. Spread AFTER
 * `rateLimitHeaders(rl)` on the SUCCESS (2xx) response only — error responses
 * must not be cached. Pass `varyOnTimezone: true` for routes that compute their
 * body from the `X-Timezone` request header (via `readTimezoneHeader`) so the
 * shared cache keys on it instead of serving one timezone's result to another.
 */
export function publicReadCacheHeaders(opts?: {
    varyOnTimezone?: boolean;
}): Record<string, string> {
    const headers: Record<string, string> = {
        "Cache-Control": PUBLIC_READ_CACHE_CONTROL,
    };
    if (opts?.varyOnTimezone) {
        headers["Vary"] = TIMEZONE_HEADER;
    }
    return headers;
}

/**
 * Header object for an optionally-personalized read: client-only cache, never
 * shared. Spread after `rateLimitHeaders(rl)` on the SUCCESS response. Pass
 * `varyOnTimezone: true` for routes that compute their body from the
 * `X-Timezone` request header so a client that changes timezone re-fetches
 * rather than reading a stale entry from its own cache (parity with the public
 * timezone-varying routes; harmless even though a client's zone rarely changes).
 */
export function privateReadCacheHeaders(opts?: {
    varyOnTimezone?: boolean;
}): Record<string, string> {
    const headers: Record<string, string> = {
        "Cache-Control": PRIVATE_READ_CACHE_CONTROL,
    };
    if (opts?.varyOnTimezone) {
        headers["Vary"] = TIMEZONE_HEADER;
    }
    return headers;
}
