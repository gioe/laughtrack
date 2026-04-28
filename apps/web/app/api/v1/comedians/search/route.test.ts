import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));
vi.mock("@/lib/data/comedian/search/getSearchedComedians", () => ({
    getSearchedComedians: vi.fn(),
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
import { getSearchedComedians } from "@/lib/data/comedian/search/getSearchedComedians";
import { rateLimitHeaders } from "@/lib/rateLimit";
import {
    RATE_LIMIT_SENTINEL_HEADER,
    RATE_LIMIT_SENTINEL_HEADERS,
    RATE_LIMIT_SENTINEL_VALUE,
} from "@/test/rateLimitSentinel";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockGetSearchedComedians = vi.mocked(getSearchedComedians);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

function makeRequest(params: Record<string, string> = {}): NextRequest {
    const url = new URL("http://localhost/api/v1/comedians/search");
    for (const [key, value] of Object.entries(params)) {
        url.searchParams.set(key, value);
    }
    return new NextRequest(url.toString());
}

const mockSearchResult = {
    data: [{ id: 1, name: "Taylor Tomlinson", isFavorite: true }],
    total: 1,
    filters: [],
};

beforeEach(() => {
    vi.clearAllMocks();
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
});

describe("GET /api/v1/comedians/search", () => {
    it("passes authenticated profile fields and admin role to the search helper", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-abc",
            userId: "user-abc",
            role: "admin",
        });
        mockGetSearchedComedians.mockResolvedValue(mockSearchResult as any);

        const res = await GET(makeRequest({ comedian: "taylor" }));
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(mockGetSearchedComedians).toHaveBeenCalledWith(
            expect.objectContaining({
                profileId: "profile-abc",
                userId: "user-abc",
                isAdmin: true,
            }),
        );
        expect(body.data[0].isFavorite).toBe(true);
    });

    it("degrades PROFILE_MISSING to anonymous search", async () => {
        mockResolveAuth.mockResolvedValue("PROFILE_MISSING");
        mockGetSearchedComedians.mockResolvedValue(mockSearchResult as any);

        const res = await GET(makeRequest());

        expect(res.status).toBe(200);
        expect(mockGetSearchedComedians).toHaveBeenCalledWith(
            expect.objectContaining({ isAdmin: false }),
        );
        expect(mockGetSearchedComedians).toHaveBeenCalledWith(
            expect.not.objectContaining({
                profileId: expect.anything(),
                userId: expect.anything(),
            }),
        );
    });

    it("returns 500 with rate-limit headers when auth resolution fails unexpectedly", async () => {
        mockResolveAuth.mockRejectedValue(
            new Error("Token verification failed"),
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
