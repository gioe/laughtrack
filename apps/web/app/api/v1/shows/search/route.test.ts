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
