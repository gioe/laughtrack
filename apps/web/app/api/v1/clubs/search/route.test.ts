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

function makeRequest(query?: string): NextRequest {
    return new NextRequest(
        `http://localhost/api/v1/clubs/search${query ? `?${query}` : ""}`,
    );
}

beforeEach(() => {
    vi.clearAllMocks();
    mockAuth.mockResolvedValue(null as never);
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
    mockGetSearchedClubs.mockResolvedValue({
        data: [],
        total: 0,
        filters: [],
        chainFilters: [],
    });
});

describe("GET /api/v1/clubs/search", () => {
    it("forwards a valid ZIP and distance to club search", async () => {
        const res = await GET(makeRequest("zip=10001&distance=50"));

        expect(res.status).toBe(200);
        expect(mockGetSearchedClubs).toHaveBeenCalledWith(
            expect.objectContaining({
                params: expect.objectContaining({
                    zip: "10001",
                    distance: "50",
                }),
            }),
        );
    });

    it("defaults the radius to 25 miles when a ZIP is supplied alone", async () => {
        await GET(makeRequest("zip=10001"));

        expect(mockGetSearchedClubs).toHaveBeenCalledWith(
            expect.objectContaining({
                params: expect.objectContaining({
                    zip: "10001",
                    distance: "25",
                }),
            }),
        );
    });

    it("preserves nationwide results when ZIP is cleared", async () => {
        await GET(makeRequest("zip=&distance=25"));

        expect(mockGetSearchedClubs).toHaveBeenCalledWith(
            expect.objectContaining({
                params: expect.objectContaining({
                    zip: undefined,
                    distance: undefined,
                }),
            }),
        );
    });

    it("rejects a non-ZIP location on the mobile API contract", async () => {
        const res = await GET(makeRequest("zip=Chicago&distance=25"));

        expect(res.status).toBe(400);
        expect(await res.json()).toEqual({
            error: "zip must be a 5-digit US postal code",
        });
        expect(mockGetSearchedClubs).not.toHaveBeenCalled();
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });

    it.each(["0", "501", "1.5", "nearby"])(
        "rejects invalid distance %s",
        async (distance) => {
            const res = await GET(
                makeRequest(`zip=10001&distance=${distance}`),
            );

            expect(res.status).toBe(400);
            expect(await res.json()).toEqual({
                error: "distance must be an integer between 1 and 500 miles",
            });
            expect(mockGetSearchedClubs).not.toHaveBeenCalled();
            expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
                RATE_LIMIT_SENTINEL_VALUE,
            );
        },
    );

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
