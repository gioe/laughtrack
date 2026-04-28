import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/data/home/getTrendingComedians", () => ({
    getTrendingComedians: vi.fn(),
}));
vi.mock("@/lib/rateLimit", () => ({
    applyPublicReadRateLimit: vi.fn(() =>
        Promise.resolve({
            allowed: true,
            limit: 60,
            remaining: 59,
            resetAt: 0,
        }),
    ),
    parseLimitParam: vi.fn(() => 8),
    rateLimitHeaders: vi.fn(),
}));

import { GET } from "./route";
import { getTrendingComedians } from "@/lib/data/home/getTrendingComedians";
import { rateLimitHeaders } from "@/lib/rateLimit";
import {
    RATE_LIMIT_SENTINEL_HEADER,
    RATE_LIMIT_SENTINEL_HEADERS,
    RATE_LIMIT_SENTINEL_VALUE,
} from "@/test/rateLimitSentinel";

const mockGetTrendingComedians = vi.mocked(getTrendingComedians);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

function makeRequest(params: Record<string, string> = {}): NextRequest {
    const url = new URL("http://localhost/api/v1/comedians");
    for (const [key, value] of Object.entries(params)) {
        url.searchParams.set(key, value);
    }
    return new NextRequest(url.toString());
}

beforeEach(() => {
    vi.clearAllMocks();
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
});

describe("GET /api/v1/comedians", () => {
    describe("offset validation", () => {
        it("returns 400 with rate-limit headers when offset is invalid", async () => {
            const res = await GET(makeRequest({ offset: "-1" }));
            const body = await res.json();

            expect(res.status).toBe(400);
            expect(body).toEqual({
                error: "offset must be a non-negative integer",
            });
            expect(mockRateLimitHeaders).toHaveBeenCalled();
            expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
                RATE_LIMIT_SENTINEL_VALUE,
            );
            expect(mockGetTrendingComedians).not.toHaveBeenCalled();
        });
    });

    describe("unexpected failures", () => {
        it("returns 500 with rate-limit headers when getTrendingComedians rejects", async () => {
            mockGetTrendingComedians.mockRejectedValue(
                new Error("DB unavailable"),
            );

            const res = await GET(makeRequest());
            const body = await res.json();

            expect(res.status).toBe(500);
            expect(body).toEqual({ error: "Failed to fetch comedians" });
            expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
                RATE_LIMIT_SENTINEL_VALUE,
            );
        });
    });
});
