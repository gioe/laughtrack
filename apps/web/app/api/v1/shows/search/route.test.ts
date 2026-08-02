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

function makeRequestWithQuery(query: string): NextRequest {
    return new NextRequest(`http://localhost/api/v1/shows/search?${query}`);
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
                    popularityScore: 42,
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
        expect(body.data[0].imageUrl).toBe("https://cdn.example.com/show.jpg");
        expect(body.data[0].popularityScore).toBe(42);
        expect(body.data[0].soldOut).toBe(false);
    });

    it("passes canonical fromDate and toDate params through to show search", async () => {
        mockGetSearchedShows.mockResolvedValue({
            data: [],
            total: 0,
            filters: [],
            zipCapTriggered: false,
        } as never);

        await GET(
            makeRequestWithQuery("fromDate=2026-06-30&toDate=2026-06-30"),
        );

        expect(mockGetSearchedShows).toHaveBeenCalledWith(
            expect.objectContaining({
                params: expect.objectContaining({
                    fromDate: "2026-06-30",
                    toDate: "2026-06-30",
                }),
            }),
        );
    });

    it("forwards a numeric clubId for exact venue scoping", async () => {
        mockGetSearchedShows.mockResolvedValue({
            data: [],
            total: 0,
            filters: [],
            zipCapTriggered: false,
        } as never);

        await GET(makeRequestWithQuery("clubId=5&club=The%20Stand"));

        expect(mockGetSearchedShows).toHaveBeenCalledWith(
            expect.objectContaining({
                params: expect.objectContaining({
                    clubId: "5",
                    club: "The Stand",
                }),
            }),
        );
    });

    it("rejects an invalid clubId", async () => {
        const res = await GET(
            makeRequestWithQuery("clubId=2147483648"),
        );

        expect(res.status).toBe(400);
        expect(await res.json()).toEqual({
            error: "clubId must be a positive integer",
        });
        expect(mockGetSearchedShows).not.toHaveBeenCalled();
    });

    it("rejects non-decimal clubId syntax", async () => {
        const res = await GET(makeRequestWithQuery("clubId=1e3"));

        expect(res.status).toBe(400);
        expect(mockGetSearchedShows).not.toHaveBeenCalled();
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
