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
 *  - `PRIVATE_READ_CACHE_CONTROL` — the per-client policy for the AUTHED branch
 *    of an optionally-personalized read (see `personalizedReadCacheHeaders`).
 *    The body differs per user, so it must NEVER enter a shared cache; `private`
 *    keeps it in the end-user's own cache only, and a short `max-age` still
 *    absorbs rapid foreground refetches. Mirrors the long-standing `home/feed`
 *    policy. The ANONYMOUS branch of the same routes is shared-cacheable instead.
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
 * Auth-bearing request headers the anonymous shared-cache variant must Vary on so
 * the CDN never serves it to an authenticated request. `Authorization` covers the
 * Bearer / mobile path; `Cookie` covers the web NextAuth session path.
 */
export const PERSONALIZED_VARY_HEADERS = ["Authorization", "Cookie"] as const;

/**
 * Header set for an OPTIONALLY-personalized read — a route that calls
 * `resolveAuth` / `auth()` and personalizes ONLY when the caller is
 * authenticated. The policy is chosen per request from the resolved auth state:
 *
 *  - `authed === true`  → the body is personalized (favorite markers,
 *    profile-scoped ordering), so `private, max-age` keeps it in the end-user's
 *    own cache only — it NEVER enters a shared cache.
 *  - `authed === false` → the body is the generic anonymous variant, so it is
 *    shared-cacheable: `public, s-maxage` lets Vercel's CDN absorb the Neon cost
 *    for anonymous traffic (the bulk of mobile reads). It Varies on
 *    `Authorization` + `Cookie` so a subsequent authed request — which carries a
 *    different value for one of those — misses this entry and falls through to
 *    the origin, which returns its own `private` response. This is the invariant
 *    that keeps personalized data out of the shared cache.
 *
 * `Vary: Cookie` fragments the anonymous *web* cache by unrelated cookies
 * (analytics, etc.), so the shared-cache win concentrates on the cookieless
 * mobile Bearer path — the intended high-volume beneficiary. Pass
 * `varyOnTimezone: true` for routes whose body depends on `readTimezoneHeader`;
 * it appends `X-Timezone` to the Vary in both branches. Spread AFTER
 * `rateLimitHeaders(rl)` on the SUCCESS (2xx) response only.
 */
export function personalizedReadCacheHeaders(opts: {
    authed: boolean;
    varyOnTimezone?: boolean;
}): Record<string, string> {
    const tz = opts.varyOnTimezone ? [TIMEZONE_HEADER] : [];
    if (opts.authed) {
        const headers: Record<string, string> = {
            "Cache-Control": PRIVATE_READ_CACHE_CONTROL,
        };
        if (tz.length) {
            headers["Vary"] = tz.join(", ");
        }
        return headers;
    }
    return {
        "Cache-Control": PUBLIC_READ_CACHE_CONTROL,
        Vary: [...PERSONALIZED_VARY_HEADERS, ...tz].join(", "),
    };
}
