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

export function getClientIp(req: Request): string {
    return (
        req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
        req.headers.get("x-real-ip") ??
        "unknown"
    );
}

/**
 * Sliding-window rate limiter.
 * @param key    Unique bucket key, e.g. "favorites:anon:1.2.3.4"
 * @param config Window size and request limit
 */
export function checkRateLimit(
    key: string,
    config: RateLimitConfig,
): RateLimitResult {
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

/** Headers to attach to every response so clients know their quota. */
export function rateLimitHeaders(
    result: RateLimitResult,
): Record<string, string> {
    return {
        "X-RateLimit-Limit": String(result.limit),
        "X-RateLimit-Remaining": String(result.remaining),
        "X-RateLimit-Reset": String(Math.ceil(result.resetAt / 1000)),
        "Retry-After": String(
            Math.ceil(Math.max(0, result.resetAt - Date.now()) / 1000),
        ),
    };
}

/** Shorthand: build a 429 response with rate-limit headers already attached. */
export function rateLimitResponse(result: RateLimitResult): NextResponse {
    return NextResponse.json(
        { error: "Too Many Requests" },
        { status: 429, headers: rateLimitHeaders(result) },
    );
}
