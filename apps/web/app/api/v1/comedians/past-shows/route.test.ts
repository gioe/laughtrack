import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));
vi.mock("@/lib/data/comedian/detail/findPastShowsForComedian", () => ({
    findPastShowsForComedian: vi.fn(),
    PAST_SHOWS_PAGE_SIZE: 12,
}));
vi.mock("@/objects/class/query/QueryHelper", () => ({
    QueryHelper: vi.fn(function QueryHelper(this: Record<string, unknown>) {
        this.params = {};
    }),
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
import { findPastShowsForComedian } from "@/lib/data/comedian/detail/findPastShowsForComedian";
import {
    RATE_LIMIT_SENTINEL_HEADER,
    RATE_LIMIT_SENTINEL_HEADERS,
    RATE_LIMIT_SENTINEL_VALUE,
} from "@/test/rateLimitSentinel";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockFindPastShowsForComedian = vi.mocked(findPastShowsForComedian);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

function makeRequest(): NextRequest {
    return new NextRequest(
        "http://localhost/api/v1/comedians/past-shows?comedian=42",
    );
}

beforeEach(() => {
    vi.clearAllMocks();
    mockResolveAuth.mockResolvedValue(null);
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
});

describe("GET /api/v1/comedians/past-shows", () => {
    // Pin the route's camelCase wire keys: the root `total`
    // (renamed from helper's `totalCount`) and show-shape camelCase fields.
    it("returns the camelCase past-shows wire shape with renamed total field", async () => {
        mockFindPastShowsForComedian.mockResolvedValue({
            shows: [
                {
                    id: 101,
                    clubId: 7,
                    clubName: "Comedy Cellar",
                    name: "Past Stop",
                    date: new Date("2025-12-01T20:00:00.000Z"),
                    imageUrl: "https://cdn.example.com/past.jpg",
                    soldOut: false,
                    lineup: [],
                    tickets: [],
                },
            ],
            totalCount: 42,
        } as never);

        const res = await GET(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.total).toBe(42);
        expect(body.data[0].clubId).toBe(7);
        expect(body.data[0].imageUrl).toBe(
            "https://cdn.example.com/past.jpg",
        );
        expect(body.data[0].soldOut).toBe(false);
    });

    it("returns 500 with rate-limit headers when the past-shows helper fails unexpectedly", async () => {
        mockFindPastShowsForComedian.mockRejectedValue(
            new Error("DB unavailable"),
        );

        const res = await GET(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(500);
        expect(body).toEqual({ error: "Failed to fetch past shows" });
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });
});
