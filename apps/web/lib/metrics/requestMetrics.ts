import { db } from "@/lib/db";

/**
 * Map an HTTP status code to its status class bucket ("2xx", "4xx", ...).
 * Bucketing by class keeps the metrics table cardinality bounded — we never
 * store the exact code, only the family. Codes outside 100–599 fall back to
 * "5xx" since they can only mean a server-side bug produced a bogus response.
 */
export function toStatusClass(status: number): string {
    const bucket = Math.floor(status / 100);
    if (bucket < 1 || bucket > 5) {
        return "5xx";
    }
    return `${bucket}xx`;
}

/**
 * Truncate a timestamp to the start of its UTC hour. This is the `hour_bucket`
 * key for the UPSERT — every request in the same wall-clock hour collides onto
 * one row so the counter table grows by at most (routes × methods × classes)
 * rows per hour.
 */
export function startOfHour(date: Date): Date {
    const bucket = new Date(date.getTime());
    bucket.setUTCMinutes(0, 0, 0);
    return bucket;
}

/**
 * Normalize a resolved request pathname into its route *pattern* by substituting
 * each resolved dynamic-segment value back with its `[param]` placeholder. This
 * is what bounds cardinality: `/api/v1/comedians/123` and `/api/v1/comedians/456`
 * both record against `/api/v1/comedians/[id]` rather than spawning a row per id.
 *
 * Catch-all segments (`params` value is an array) collapse to `[...param]`.
 * Substitution is anchored to full path segments — a leading "/" and a trailing
 * "/" or end-of-string — so a param value can never match a coincidental
 * substring of a static segment. The greedy `(.*)` prefix anchors to the LAST
 * matching run of segments: dynamic segments are the trailing/most-specific part
 * of these routes, so when a value coincides with an earlier static segment
 * (e.g. `/api/clubs/clubs` with `id="clubs"`) the trailing segment is collapsed
 * (`/api/clubs/[id]`), not the earlier one.
 */
export function normalizeRoutePattern(
    pathname: string,
    params?: Record<string, string | string[]>,
): string {
    if (!params) {
        return pathname;
    }

    let pattern = pathname;
    for (const [key, value] of Object.entries(params)) {
        if (Array.isArray(value)) {
            const joined = value.map(escapeRegExp).join("/");
            if (joined) {
                pattern = pattern.replace(
                    new RegExp(`^(.*)/${joined}(?=/|$)`),
                    `$1/[...${key}]`,
                );
            }
        } else if (value) {
            pattern = pattern.replace(
                new RegExp(`^(.*)/${escapeRegExp(value)}(?=/|$)`),
                `$1/[${key}]`,
            );
        }
    }
    return pattern;
}

function escapeRegExp(literal: string): string {
    return literal.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export interface RequestMetric {
    routePattern: string;
    method: string;
    status: number;
    /** Injectable clock for deterministic tests; defaults to the current time. */
    now?: Date;
}

/**
 * Record a single API request as a bucketed counter increment.
 *
 * Performs an UPSERT against `api_request_metrics`: the first request in a
 * (route_pattern, method, status_class, hour_bucket) tuple inserts a row with
 * count = 1; every subsequent one increments. `updated_at` is set to NOW()
 * explicitly on both the insert and the conflict update — Prisma's `@updatedAt`
 * only fires through the query builder, never on raw SQL, so the column would
 * otherwise go stale.
 *
 * This is intended to run off the response critical path (see withRequestMetrics).
 */
export async function recordRequestMetric({
    routePattern,
    method,
    status,
    now = new Date(),
}: RequestMetric): Promise<void> {
    const statusClass = toStatusClass(status);
    const hourBucket = startOfHour(now);

    await db.$executeRaw`
        INSERT INTO api_request_metrics
            (route_pattern, method, status_class, hour_bucket, count, created_at, updated_at)
        VALUES (${routePattern}, ${method}, ${statusClass}, ${hourBucket}, 1, NOW(), NOW())
        ON CONFLICT (route_pattern, method, status_class, hour_bucket)
        DO UPDATE SET
            count = api_request_metrics.count + 1,
            updated_at = NOW()
    `;
}
