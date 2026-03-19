import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";
import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";

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
    /** Public read endpoints — anonymous callers. */
    publicRead: { limit: 60, windowMs: 60_000 } satisfies RateLimitConfig,
    /** Public read endpoints — authenticated callers (higher allowance). */
    publicReadAuth: { limit: 300, windowMs: 60_000 } satisfies RateLimitConfig,
    /** Token-exchange endpoint — stricter per-IP limit. */
    authToken: { limit: 10, windowMs: 60_000 } satisfies RateLimitConfig,
} as const;

// ---------------------------------------------------------------------------
// Upstash Redis — initialised lazily when env vars are present.
// Falls back to the in-memory store when the vars are absent (local dev).
// ---------------------------------------------------------------------------

// Shared Redis client — created once when env vars are present.
let _redis: Redis | null = null;
function getRedis(): Redis | null {
    if (_redis !== null) return _redis;
    const url = process.env.UPSTASH_REDIS_REST_URL;
    const token = process.env.UPSTASH_REDIS_REST_TOKEN;
    if (!url || !token) return null;
    _redis = new Redis({ url, token });
    return _redis;
}

function buildUpstashLimiter(config: RateLimitConfig): Ratelimit | null {
    const redis = getRedis();
    if (!redis) return null;
    return new Ratelimit({
        redis,
        limiter: Ratelimit.slidingWindow(config.limit, `${config.windowMs} ms`),
        analytics: false,
    });
}

// Cached limiters — one per config window+limit combo to avoid rebuilding on every call.
const _limiterCache = new Map<string, Ratelimit | null>();
function getLimiter(config: RateLimitConfig): Ratelimit | null {
    const cacheKey = `${config.limit}:${config.windowMs}`;
    if (!_limiterCache.has(cacheKey)) {
        _limiterCache.set(cacheKey, buildUpstashLimiter(config));
    }
    return _limiterCache.get(cacheKey)!;
}

// ---------------------------------------------------------------------------
// In-memory fallback (local dev / no Upstash credentials)
// ---------------------------------------------------------------------------
const store = new Map<string, RateLimitWindow>();

const STORE_CLEANUP_THRESHOLD = 5_000;
function maybePruneStore(): void {
    if (store.size < STORE_CLEANUP_THRESHOLD) return;
    const now = Date.now();
    for (const [key, entry] of store) {
        if (now >= entry.resetAt) store.delete(key);
    }
}

function checkRateLimitInMemory(
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
 * Fixed/sliding-window rate limiter.
 *
 * Delegates to Upstash Redis when UPSTASH_REDIS_REST_URL and
 * UPSTASH_REDIS_REST_TOKEN are set (production), otherwise falls back to an
 * in-memory store (local development).
 *
 * @param key    Unique bucket key, e.g. "favorites:anon:1.2.3.4"
 * @param config Window size and request limit
 */
export async function checkRateLimit(
    key: string,
    config: RateLimitConfig,
): Promise<RateLimitResult> {
    const limiter = getLimiter(config);

    if (limiter) {
        try {
            const result = await limiter.limit(key);
            return {
                allowed: result.success,
                limit: result.limit,
                remaining: result.remaining,
                resetAt: result.reset,
            };
        } catch {
            // Upstash unavailable — degrade gracefully to in-memory fallback.
            return checkRateLimitInMemory(key, config);
        }
    }

    return checkRateLimitInMemory(key, config);
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

/**
 * Apply the standard public-read rate limit (auth vs anon) for a given route prefix.
 * Returns the RateLimitResult on success, or a 429 NextResponse if the limit is exceeded.
 *
 * Usage:
 *   const rl = await applyPublicReadRateLimit(req, "clubs");
 *   if (rl instanceof NextResponse) return rl;
 */
export async function applyPublicReadRateLimit(
    req: NextRequest,
    routePrefix: string,
): Promise<RateLimitResult | NextResponse> {
    const session = await auth();
    const isAuthenticated = !!session?.profile;
    const rateLimitKey = isAuthenticated
        ? `${routePrefix}:auth:${session!.profile!.userid}`
        : `${routePrefix}:anon:${getClientIp(req)}`;
    const rl = await checkRateLimit(
        rateLimitKey,
        isAuthenticated ? RATE_LIMITS.publicReadAuth : RATE_LIMITS.publicRead,
    );
    if (!rl.allowed) return rateLimitResponse(rl);
    return rl;
}

/**
 * Parse and validate the "limit" query parameter (integer, 1–100).
 * Returns the parsed number, or a 400 NextResponse if invalid.
 *
 * Usage:
 *   const limitOrErr = parseLimitParam(req);
 *   if (limitOrErr instanceof NextResponse) return limitOrErr;
 */
export function parseLimitParam(
    req: NextRequest,
    defaultValue = 8,
): number | NextResponse {
    const raw = req.nextUrl.searchParams.get("limit");
    const limit = raw !== null ? Number(raw) : defaultValue;
    if (!Number.isInteger(limit) || limit < 1 || limit > 100) {
        return NextResponse.json(
            { error: "limit must be a positive integer between 1 and 100" },
            { status: 400 },
        );
    }
    return limit;
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
