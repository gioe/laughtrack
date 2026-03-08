import { NextResponse } from "next/server";

interface RateLimitWindow {
    count: number;
    resetAt: number;
}

interface RateLimitConfig {
    limit: number;
    windowMs: number;
}

export interface RateLimitResult {
    allowed: boolean;
    limit: number;
    remaining: number;
    resetAt: number;
}

export const RATE_LIMITS = {
    /** Higher limit for identified (authenticated) users. */
    authenticated: { limit: 100, windowMs: 60_000 } satisfies RateLimitConfig,
    /** Strict limit for anonymous / unauthenticated requests. */
    unauthenticated: { limit: 20, windowMs: 60_000 } satisfies RateLimitConfig,
    /** Very tight limit for one-shot public actions like unsubscribe. */
    unsubscribe: { limit: 5, windowMs: 600_000 } satisfies RateLimitConfig,
} as const;

// In-memory store. Resets on server restart / cold start (acceptable for edge rate-limiting).
const store = new Map<string, RateLimitWindow>();

// Evict expired entries when the store grows large to prevent unbounded memory growth.
const STORE_CLEANUP_THRESHOLD = 5_000;
function maybePruneStore(): void {
    if (store.size < STORE_CLEANUP_THRESHOLD) return;
    const now = Date.now();
    for (const [key, entry] of store) {
        if (now >= entry.resetAt) store.delete(key);
    }
}

/**
 * Returns the client IP from request headers.
 *
 * IMPORTANT: This trusts the rightmost IP in x-forwarded-for that is not
 * added by the client (i.e., infrastructure-injected). In production this
 * assumes the deployment sits behind a reverse proxy (e.g., Vercel, AWS ALB)
 * that appends the real client IP and strips any client-supplied values.
 * Without a trusted proxy, callers can spoof this header.
 */
export function getClientIp(req: Request): string {
    // x-real-ip is set by Nginx/Vercel with the actual client IP — prefer it.
    const realIp = req.headers.get("x-real-ip")?.trim();
    if (realIp) return realIp;

    // Fall back to the rightmost entry in x-forwarded-for that is
    // infrastructure-added (proxies append, so the last value is most trusted).
    const forwarded = req.headers.get("x-forwarded-for");
    if (forwarded) {
        const parts = forwarded.split(",").map((s) => s.trim());
        const ip = parts[parts.length - 1];
        if (ip) return ip;
    }

    return "unknown";
}

/**
 * Fixed-window rate limiter.
 * @param key    Unique bucket key, e.g. "favorites:anon:1.2.3.4"
 * @param config Window size and request limit
 */
export function checkRateLimit(
    key: string,
    config: RateLimitConfig,
): RateLimitResult {
    maybePruneStore();
    const now = Date.now();
    const entry = store.get(key);

    if (!entry || now >= entry.resetAt) {
        const resetAt = now + config.windowMs;
        store.set(key, { count: 1, resetAt });
        return {
            allowed: true,
            limit: config.limit,
            remaining: config.limit - 1,
            resetAt,
        };
    }

    entry.count += 1;
    const remaining = Math.max(0, config.limit - entry.count);
    return {
        allowed: entry.count <= config.limit,
        limit: config.limit,
        remaining,
        resetAt: entry.resetAt,
    };
}

/**
 * Quota headers for every response (200, 4xx, etc.) so clients can track usage.
 * Does NOT include Retry-After — that header is only meaningful on 429/503 (RFC 7231).
 */
export function rateLimitHeaders(
    result: RateLimitResult,
): Record<string, string> {
    return {
        "X-RateLimit-Limit": String(result.limit),
        "X-RateLimit-Remaining": String(result.remaining),
        "X-RateLimit-Reset": String(Math.ceil(result.resetAt / 1000)),
    };
}

/** Shorthand: build a 429 response with quota + Retry-After headers attached. */
export function rateLimitResponse(result: RateLimitResult): NextResponse {
    return NextResponse.json(
        { error: "Too Many Requests" },
        {
            status: 429,
            headers: {
                ...rateLimitHeaders(result),
                "Retry-After": String(
                    Math.ceil(Math.max(0, result.resetAt - Date.now()) / 1000),
                ),
            },
        },
    );
}
