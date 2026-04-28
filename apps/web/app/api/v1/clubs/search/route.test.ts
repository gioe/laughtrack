import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));
vi.mock("@/lib/data/club/search/getSearchedClubs", () => ({
    getSearchedClubs: vi.fn(),
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
import { auth } from "@/auth";
import { rateLimitHeaders } from "@/lib/rateLimit";
import { getSearchedClubs } from "@/lib/data/club/search/getSearchedClubs";
import {
    RATE_LIMIT_SENTINEL_HEADER,
    RATE_LIMIT_SENTINEL_HEADERS,
    RATE_LIMIT_SENTINEL_VALUE,
} from "@/test/rateLimitSentinel";

const mockAuth = vi.mocked(auth);
const mockGetSearchedClubs = vi.mocked(getSearchedClubs);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

function makeRequest(): NextRequest {
    return new NextRequest("http://localhost/api/v1/clubs/search");
}

beforeEach(() => {
    vi.clearAllMocks();
    mockAuth.mockResolvedValue(null as any);
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
});

describe("GET /api/v1/clubs/search", () => {
    it("returns 500 with rate-limit headers when the search helper fails unexpectedly", async () => {
        mockGetSearchedClubs.mockRejectedValue(new Error("DB unavailable"));

        const res = await GET(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(500);
        expect(body).toEqual({ error: "Failed to fetch clubs" });
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });
});
