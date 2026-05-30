import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/db", () => ({
    db: { $queryRaw: vi.fn() },
}));

import { db } from "@/lib/db";
import {
    DEFAULT_API_REQUEST_RANGE,
    getApiRequestMetrics,
    resolveApiRequestRange,
} from "./apiRequests";

const mockQueryRaw = vi.mocked(db.$queryRaw);

beforeEach(() => {
    vi.clearAllMocks();
});

describe("resolveApiRequestRange", () => {
    it("resolves a known range key to its hour window", () => {
        expect(resolveApiRequestRange("7d")).toMatchObject({
            key: "7d",
            hours: 24 * 7,
        });
    });

    it("falls back to the default range for an unknown key", () => {
        expect(resolveApiRequestRange("bogus").key).toBe(
            DEFAULT_API_REQUEST_RANGE,
        );
    });

    it("falls back to the default range when the param is absent", () => {
        expect(resolveApiRequestRange(undefined).key).toBe(
            DEFAULT_API_REQUEST_RANGE,
        );
    });
});

describe("getApiRequestMetrics", () => {
    it("coerces bigint rows, computes error rate, and defaults the trend to the busiest route", async () => {
        const firstBucket = new Date("2026-05-29T00:00:00Z");
        const lastBucket = new Date("2026-05-29T05:00:00Z");
        mockQueryRaw
            .mockResolvedValueOnce([
                {
                    total_requests: BigInt(1000),
                    error_requests: BigInt(50),
                    distinct_routes: BigInt(8),
                    first_bucket: firstBucket,
                    last_bucket: lastBucket,
                },
            ] as never)
            .mockResolvedValueOnce([
                {
                    route_pattern: "/api/a",
                    count: BigInt(600),
                    error_count: BigInt(30),
                },
                {
                    route_pattern: "/api/b",
                    count: BigInt(400),
                    error_count: BigInt(20),
                },
            ] as never)
            .mockResolvedValueOnce([
                { key: "2xx", count: BigInt(950) },
                { key: "4xx", count: BigInt(50) },
            ] as never)
            .mockResolvedValueOnce([
                { key: "GET", count: BigInt(1000) },
            ] as never)
            .mockResolvedValueOnce([
                {
                    hour_bucket: new Date("2026-05-29T05:00:00Z"),
                    count: BigInt(100),
                    error_count: BigInt(5),
                },
            ] as never);

        const data = await getApiRequestMetrics({ rangeParam: "7d" });

        expect(data.range.key).toBe("7d");
        expect(data.totals).toMatchObject({
            totalRequests: 1000,
            errorRequests: 50,
            errorRate: 0.05,
            distinctRoutes: 8,
            firstBucket: firstBucket.toISOString(),
            lastBucket: lastBucket.toISOString(),
        });
        expect(data.topRoutes[0]).toEqual({
            routePattern: "/api/a",
            count: 600,
            errorCount: 30,
        });
        expect(data.statusBreakdown).toEqual([
            { key: "2xx", count: 950 },
            { key: "4xx", count: 50 },
        ]);
        expect(data.methodBreakdown).toEqual([{ key: "GET", count: 1000 }]);
        // No explicit route param -> trend defaults to the busiest route.
        expect(data.selectedRoute).toBe("/api/a");
        expect(data.routeTrend).toEqual([
            {
                hourBucket: "2026-05-29T05:00:00.000Z",
                count: 100,
                errorCount: 5,
            },
        ]);
    });

    it("guards divide-by-zero and skips the trend query when there are no routes", async () => {
        mockQueryRaw
            .mockResolvedValueOnce([
                {
                    total_requests: BigInt(0),
                    error_requests: BigInt(0),
                    distinct_routes: BigInt(0),
                    first_bucket: null,
                    last_bucket: null,
                },
            ] as never)
            .mockResolvedValueOnce([] as never) // topRoutes
            .mockResolvedValueOnce([] as never) // status
            .mockResolvedValueOnce([] as never); // method

        const data = await getApiRequestMetrics({});

        expect(data.totals.errorRate).toBe(0);
        expect(data.totals.firstBucket).toBeNull();
        expect(data.selectedRoute).toBeNull();
        expect(data.routeTrend).toEqual([]);
        // Only the four aggregate queries ran; the trend query is skipped.
        expect(mockQueryRaw).toHaveBeenCalledTimes(4);
    });

    it("honors an explicit in-window route over the busiest one", async () => {
        mockQueryRaw
            .mockResolvedValueOnce([
                {
                    total_requests: BigInt(1000),
                    error_requests: BigInt(0),
                    distinct_routes: BigInt(2),
                    first_bucket: null,
                    last_bucket: null,
                },
            ] as never)
            .mockResolvedValueOnce([
                {
                    route_pattern: "/api/a",
                    count: BigInt(600),
                    error_count: BigInt(0),
                },
                {
                    route_pattern: "/api/b",
                    count: BigInt(400),
                    error_count: BigInt(0),
                },
            ] as never)
            .mockResolvedValueOnce([] as never)
            .mockResolvedValueOnce([] as never)
            .mockResolvedValueOnce([] as never); // trend for /api/b

        const data = await getApiRequestMetrics({ routeParam: "/api/b" });

        expect(data.selectedRoute).toBe("/api/b");
    });

    it("falls back to the busiest route when the requested route is not in the window", async () => {
        mockQueryRaw
            .mockResolvedValueOnce([
                {
                    total_requests: BigInt(600),
                    error_requests: BigInt(0),
                    distinct_routes: BigInt(1),
                    first_bucket: null,
                    last_bucket: null,
                },
            ] as never)
            .mockResolvedValueOnce([
                {
                    route_pattern: "/api/a",
                    count: BigInt(600),
                    error_count: BigInt(0),
                },
            ] as never)
            .mockResolvedValueOnce([] as never)
            .mockResolvedValueOnce([] as never)
            .mockResolvedValueOnce([] as never); // trend for /api/a

        const data = await getApiRequestMetrics({ routeParam: "/api/missing" });

        expect(data.selectedRoute).toBe("/api/a");
    });
});
