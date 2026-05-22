import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));
vi.mock("@/lib/data/show/search/getSearchedShows", () => ({
    getSearchedShows: vi.fn(),
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
import { resolveAuth } from "@/lib/auth/resolveAuth";
import { rateLimitHeaders } from "@/lib/rateLimit";
import { getSearchedShows } from "@/lib/data/show/search/getSearchedShows";
import {
    RATE_LIMIT_SENTINEL_HEADER,
    RATE_LIMIT_SENTINEL_HEADERS,
    RATE_LIMIT_SENTINEL_VALUE,
} from "@/test/rateLimitSentinel";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockGetSearchedShows = vi.mocked(getSearchedShows);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

function makeRequest(): NextRequest {
    return new NextRequest("http://localhost/api/v1/shows/search");
}

beforeEach(() => {
    vi.clearAllMocks();
    mockResolveAuth.mockResolvedValue(null);
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
});

describe("GET /api/v1/shows/search", () => {
    // Pin camelCase wire keys distinctive to this route: `zipCapTriggered`
    // (root) and a representative show field, so a future regression
    // (e.g. zipCapTriggered → zip_cap_triggered) surfaces here.
    it("returns the camelCase search wire shape including zipCapTriggered", async () => {
        mockGetSearchedShows.mockResolvedValue({
            data: [
                {
                    id: 1,
                    clubId: 7,
                    name: "Show",
                    date: new Date("2026-07-04T20:00:00.000Z"),
                    imageUrl: "https://cdn.example.com/show.jpg",
                    soldOut: false,
                    lineup: [],
                },
            ],
            total: 1,
            filters: [],
            zipCapTriggered: false,
        } as never);

        const res = await GET(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.total).toBe(1);
        expect(body.zipCapTriggered).toBe(false);
        expect(body.data[0].clubId).toBe(7);
        expect(body.data[0].imageUrl).toBe(
            "https://cdn.example.com/show.jpg",
        );
        expect(body.data[0].soldOut).toBe(false);
    });

    it("returns 500 with rate-limit headers when the search helper fails unexpectedly", async () => {
        mockGetSearchedShows.mockRejectedValue(new Error("DB unavailable"));

        const res = await GET(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(500);
        expect(body).toEqual({ error: "Failed to fetch shows" });
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });
});
