import { db } from "@/lib/db";

/**
 * Selectable time windows for the api_request_metrics admin view. The keys are
 * stable URL slugs (used as the `range` searchParam); `hours` drives the SQL
 * window via `make_interval(hours => ...)`.
 */
export const API_REQUEST_RANGES = [
    { key: "24h", label: "Last 24h", hours: 24 },
    { key: "7d", label: "Last 7d", hours: 24 * 7 },
    { key: "30d", label: "Last 30d", hours: 24 * 30 },
] as const;

export type ApiRequestRangeKey = (typeof API_REQUEST_RANGES)[number]["key"];

export const DEFAULT_API_REQUEST_RANGE: ApiRequestRangeKey = "24h";

export function resolveApiRequestRange(
    rangeParam: string | undefined,
): (typeof API_REQUEST_RANGES)[number] {
    return (
        API_REQUEST_RANGES.find((range) => range.key === rangeParam) ??
        API_REQUEST_RANGES.find(
            (range) => range.key === DEFAULT_API_REQUEST_RANGE,
        )!
    );
}

// 4xx + 5xx status classes are treated as errors for the error-rate summary.

function toNumber(value: bigint | number | null | undefined): number {
    if (value === null || value === undefined) return 0;
    return typeof value === "bigint" ? Number(value) : value;
}

function toIso(value: Date | string | null): string | null {
    if (value === null) return null;
    return value instanceof Date ? value.toISOString() : value;
}

export type ApiRequestTotals = {
    totalRequests: number;
    errorRequests: number;
    errorRate: number; // 0..1
    distinctRoutes: number;
    firstBucket: string | null;
    lastBucket: string | null;
};

export type RouteVolume = {
    routePattern: string;
    count: number;
    errorCount: number;
};

export type BreakdownRow = {
    key: string;
    count: number;
};

export type TrendPoint = {
    hourBucket: string;
    count: number;
    errorCount: number;
};

export type ApiRequestMetricsData = {
    range: (typeof API_REQUEST_RANGES)[number];
    totals: ApiRequestTotals;
    topRoutes: RouteVolume[];
    statusBreakdown: BreakdownRow[];
    methodBreakdown: BreakdownRow[];
    selectedRoute: string | null;
    routeTrend: TrendPoint[];
};

type TotalsRow = {
    total_requests: bigint | number | null;
    error_requests: bigint | number | null;
    distinct_routes: bigint | number | null;
    first_bucket: Date | string | null;
    last_bucket: Date | string | null;
};

type RouteVolumeRow = {
    route_pattern: string;
    count: bigint | number;
    error_count: bigint | number;
};

type BreakdownDbRow = {
    key: string;
    count: bigint | number;
};

type TrendRow = {
    hour_bucket: Date | string;
    count: bigint | number;
    error_count: bigint | number;
};

/**
 * Aggregate api_request_metrics for the admin dashboard. All counts are summed
 * over the selected window. `routeParam` selects which route the per-route
 * trend reports on; when absent (or not present in the window) it falls back to
 * the highest-volume route so the trend chart is never empty.
 */
export async function getApiRequestMetrics({
    rangeParam,
    routeParam,
}: {
    rangeParam?: string;
    routeParam?: string;
}): Promise<ApiRequestMetricsData> {
    const range = resolveApiRequestRange(rangeParam);
    const hours = range.hours;

    const [totalsRows, topRouteRows, statusRows, methodRows] =
        await Promise.all([
            db.$queryRaw<TotalsRow[]>`
                SELECT
                    COALESCE(SUM(count), 0) AS total_requests,
                    COALESCE(SUM(count) FILTER (
                        WHERE status_class IN ('4xx', '5xx')
                    ), 0) AS error_requests,
                    COUNT(DISTINCT route_pattern) AS distinct_routes,
                    MIN(hour_bucket) AS first_bucket,
                    MAX(hour_bucket) AS last_bucket
                FROM api_request_metrics
                WHERE hour_bucket >= NOW() - make_interval(hours => ${hours})
            `,
            db.$queryRaw<RouteVolumeRow[]>`
                SELECT
                    route_pattern,
                    SUM(count) AS count,
                    COALESCE(SUM(count) FILTER (
                        WHERE status_class IN ('4xx', '5xx')
                    ), 0) AS error_count
                FROM api_request_metrics
                WHERE hour_bucket >= NOW() - make_interval(hours => ${hours})
                GROUP BY route_pattern
                ORDER BY SUM(count) DESC
                LIMIT 20
            `,
            db.$queryRaw<BreakdownDbRow[]>`
                SELECT status_class AS key, SUM(count) AS count
                FROM api_request_metrics
                WHERE hour_bucket >= NOW() - make_interval(hours => ${hours})
                GROUP BY status_class
                ORDER BY SUM(count) DESC
            `,
            db.$queryRaw<BreakdownDbRow[]>`
                SELECT method AS key, SUM(count) AS count
                FROM api_request_metrics
                WHERE hour_bucket >= NOW() - make_interval(hours => ${hours})
                GROUP BY method
                ORDER BY SUM(count) DESC
            `,
        ]);

    const topRoutes: RouteVolume[] = topRouteRows.map((row) => ({
        routePattern: row.route_pattern,
        count: toNumber(row.count),
        errorCount: toNumber(row.error_count),
    }));

    // Pick the route for the trend: an explicit, in-window selection wins;
    // otherwise default to the busiest route.
    const selectedRoute =
        (routeParam &&
            topRoutes.find((route) => route.routePattern === routeParam)
                ?.routePattern) ||
        topRoutes[0]?.routePattern ||
        null;

    const trendRows = selectedRoute
        ? await db.$queryRaw<TrendRow[]>`
                SELECT
                    hour_bucket,
                    SUM(count) AS count,
                    COALESCE(SUM(count) FILTER (
                        WHERE status_class IN ('4xx', '5xx')
                    ), 0) AS error_count
                FROM api_request_metrics
                WHERE hour_bucket >= NOW() - make_interval(hours => ${hours})
                  AND route_pattern = ${selectedRoute}
                GROUP BY hour_bucket
                ORDER BY hour_bucket ASC
            `
        : [];

    const totalsRow = totalsRows[0];
    const totalRequests = toNumber(totalsRow?.total_requests);
    const errorRequests = toNumber(totalsRow?.error_requests);

    return {
        range,
        totals: {
            totalRequests,
            errorRequests,
            errorRate: totalRequests > 0 ? errorRequests / totalRequests : 0,
            distinctRoutes: toNumber(totalsRow?.distinct_routes),
            firstBucket: toIso(totalsRow?.first_bucket ?? null),
            lastBucket: toIso(totalsRow?.last_bucket ?? null),
        },
        topRoutes,
        statusBreakdown: statusRows.map((row) => ({
            key: row.key,
            count: toNumber(row.count),
        })),
        methodBreakdown: methodRows.map((row) => ({
            key: row.key,
            count: toNumber(row.count),
        })),
        selectedRoute,
        routeTrend: trendRows.map((row) => ({
            hourBucket: toIso(row.hour_bucket) ?? "",
            count: toNumber(row.count),
            errorCount: toNumber(row.error_count),
        })),
    };
}
