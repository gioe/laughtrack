import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));
vi.mock("@/lib/data/show/search/findShowsWithCount", () => ({
    findUpcomingShowsForClub: vi.fn(),
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
import { findUpcomingShowsForClub } from "@/lib/data/show/search/findShowsWithCount";
import {
    RATE_LIMIT_SENTINEL_HEADER,
    RATE_LIMIT_SENTINEL_HEADERS,
    RATE_LIMIT_SENTINEL_VALUE,
} from "@/test/rateLimitSentinel";
import { expectOpenApiResponse } from "@/test/openapiResponseValidator";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockFindUpcomingShowsForClub = vi.mocked(findUpcomingShowsForClub);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

function makeRequest(url = "http://localhost/api/v1/clubs/7/shows") {
    return new NextRequest(url);
}

beforeEach(() => {
    vi.clearAllMocks();
    mockResolveAuth.mockResolvedValue(null);
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
});

describe("GET /api/v1/clubs/[id]/shows", () => {
    it("returns upcoming shows for a club matching the OpenAPI contract", async () => {
        mockFindUpcomingShowsForClub.mockResolvedValue({
            shows: [
                {
                    id: 11,
                    clubId: 7,
                    clubName: "Comedy Cellar",
                    clubCity: "New York",
                    clubState: "NY",
                    name: "Late Show",
                    date: new Date("2026-07-04T20:00:00.000Z"),
                    imageUrl: "https://cdn.example.com/club.jpg",
                    soldOut: false,
                    lineup: [],
                    tickets: [],
                },
            ],
            totalCount: 1,
            zipCapTriggered: false,
        } as never);

        const res = await GET(
            makeRequest("http://localhost/api/v1/clubs/7/shows?page=0&size=5"),
            {
                params: Promise.resolve({ id: "7" }),
            },
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(mockFindUpcomingShowsForClub).toHaveBeenCalledWith(7, {
            page: "1",
            size: "5",
        });
        expectOpenApiResponse("/clubs/{id}/shows", 200, body);
    });

    it("returns 400 for an invalid id", async () => {
        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "abc" }),
        });
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body).toEqual({ error: "Invalid id" });
        expect(mockFindUpcomingShowsForClub).not.toHaveBeenCalled();
    });

    it("returns 500 with rate-limit headers when the lookup fails unexpectedly", async () => {
        mockFindUpcomingShowsForClub.mockRejectedValue(
            new Error("DB unavailable"),
        );

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "7" }),
        });
        const body = await res.json();

        expect(res.status).toBe(500);
        expect(body).toEqual({ error: "Failed to fetch club shows" });
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });
});
