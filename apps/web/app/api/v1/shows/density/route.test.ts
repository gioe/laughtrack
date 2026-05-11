import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/data/show/search/findShowDensity", () => ({
    findShowDensity: vi.fn(),
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
    rateLimitHeaders: vi.fn(),
}));

import { GET } from "./route";
import { findShowDensity } from "@/lib/data/show/search/findShowDensity";
import { rateLimitHeaders } from "@/lib/rateLimit";
import {
    RATE_LIMIT_SENTINEL_HEADER,
    RATE_LIMIT_SENTINEL_HEADERS,
    RATE_LIMIT_SENTINEL_VALUE,
} from "@/test/rateLimitSentinel";

const mockFindShowDensity = vi.mocked(findShowDensity);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

function makeRequest(params: Record<string, string> = {}): NextRequest {
    const url = new URL("http://localhost/api/v1/shows/density");
    for (const [key, value] of Object.entries(params)) {
        url.searchParams.set(key, value);
    }
    return new NextRequest(url.toString(), {
        headers: { "X-Timezone": "America/New_York" },
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    mockFindShowDensity.mockResolvedValue({ "2026-06-01": 2 });
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
});

describe("GET /api/v1/shows/density", () => {
    it("returns show counts keyed by ISO date", async () => {
        const res = await GET(
            makeRequest({
                from: "2026-06-01",
                to: "2026-06-07",
                zip: "10012",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body).toEqual({ "2026-06-01": 2 });
        expect(mockFindShowDensity).toHaveBeenCalledWith(
            expect.objectContaining({
                params: expect.objectContaining({
                    fromDate: "2026-06-01",
                    toDate: "2026-06-07",
                    zip: "10012",
                    distance: "25",
                }),
                timezone: "America/New_York",
            }),
        );
    });

    it("respects the optional distance parameter", async () => {
        await GET(
            makeRequest({
                from: "2026-06-01",
                to: "2026-06-07",
                zip: "10012",
                distance: "50",
            }),
        );

        expect(mockFindShowDensity).toHaveBeenCalledWith(
            expect.objectContaining({
                params: expect.objectContaining({ distance: "50" }),
            }),
        );
    });

    it("caps ranges longer than 90 days", async () => {
        await GET(
            makeRequest({
                from: "2026-06-01",
                to: "2026-12-31",
                zip: "10012",
            }),
        );

        expect(mockFindShowDensity).toHaveBeenCalledWith(
            expect.objectContaining({
                params: expect.objectContaining({
                    fromDate: "2026-06-01",
                    toDate: "2026-08-29",
                }),
            }),
        );
    });

    it("handles missing zip by searching all visible club locations", async () => {
        const res = await GET(
            makeRequest({ from: "2026-06-01", to: "2026-06-07" }),
        );

        expect(res.status).toBe(200);
        expect(mockFindShowDensity).toHaveBeenCalledWith(
            expect.objectContaining({
                params: expect.objectContaining({
                    zip: undefined,
                    distance: undefined,
                }),
            }),
        );
    });

    it("returns 400 when distance is invalid", async () => {
        const res = await GET(
            makeRequest({
                from: "2026-06-01",
                to: "2026-06-07",
                zip: "10012",
                distance: "0",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body.error).toMatch(/distance/i);
    });

    it("returns 400 when to is before from", async () => {
        const res = await GET(
            makeRequest({
                from: "2026-06-07",
                to: "2026-06-01",
                zip: "10012",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body.error).toMatch(/to/i);
    });

    it("returns 500 with rate-limit headers when the density helper fails unexpectedly", async () => {
        mockFindShowDensity.mockRejectedValue(new Error("DB unavailable"));

        const res = await GET(
            makeRequest({
                from: "2026-06-01",
                to: "2026-06-07",
                zip: "10012",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(500);
        expect(body).toEqual({ error: "Failed to fetch show density" });
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });
});
