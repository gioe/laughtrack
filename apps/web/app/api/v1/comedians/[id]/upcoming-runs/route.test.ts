import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/data/comedian/detail/findUpcomingRunsForComedian", () => ({
    findUpcomingRunsForComedian: vi.fn(),
}));
vi.mock("@/lib/auth/resolveAuth", () => ({
    PROFILE_MISSING: Symbol.for("PROFILE_MISSING"),
    resolveAuth: vi.fn(() => Promise.resolve(Symbol.for("PROFILE_MISSING"))),
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
import { findUpcomingRunsForComedian } from "@/lib/data/comedian/detail/findUpcomingRunsForComedian";
import { rateLimitHeaders } from "@/lib/rateLimit";
import {
    RATE_LIMIT_SENTINEL_HEADER,
    RATE_LIMIT_SENTINEL_HEADERS,
    RATE_LIMIT_SENTINEL_VALUE,
} from "@/test/rateLimitSentinel";
import { expectOpenApiResponse } from "@/test/openapiResponseValidator";

const mockFindUpcomingRuns = vi.mocked(findUpcomingRunsForComedian);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

function makeRequest(query = ""): NextRequest {
    return new NextRequest(
        `http://localhost/api/v1/comedians/123/upcoming-runs${query}`,
        { headers: { "X-Timezone": "America/New_York" } },
    );
}

beforeEach(() => {
    vi.clearAllMocks();
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
});

describe("GET /api/v1/comedians/[id]/upcoming-runs", () => {
    it("returns grouped upcoming runs using the iOS OpenAPI response shape", async () => {
        mockFindUpcomingRuns.mockResolvedValue([
            {
                clubID: 10,
                clubName: "Comedy Cellar",
                clubImageUrl: "https://cdn.example.com/club.jpg",
                shows: [
                    {
                        id: 101,
                        clubID: 10,
                        clubName: "Comedy Cellar",
                        date: new Date("2026-07-01T23:00:00.000Z"),
                        tickets: [],
                        name: "Tour Stop",
                        description: undefined,
                        address: "117 MacDougal St, New York, NY",
                        room: null,
                        imageUrl: "https://cdn.example.com/club.jpg",
                        soldOut: false,
                        lineup: [],
                        distanceMiles: null,
                        timezone: "America/New_York",
                    },
                ],
            },
        ]);

        const res = await GET(
            makeRequest("?club=cellar&location=New%20York&date=2026-07-01"),
            { params: Promise.resolve({ id: "123" }) },
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expectOpenApiResponse("/comedians/{id}/upcoming-runs", 200, body);
        expect(body.data[0].shows).toHaveLength(1);
        expect(mockFindUpcomingRuns).toHaveBeenCalledWith(123, {
            club: "cellar",
            location: "New York",
            date: "2026-07-01",
            timezone: "America/New_York",
        });
    });

    it("returns 400 for a malformed date", async () => {
        const res = await GET(makeRequest("?date=07-01-2026"), {
            params: Promise.resolve({ id: "123" }),
        });
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body).toEqual({
            error: "date must be a valid date in YYYY-MM-DD format",
        });
        expect(mockFindUpcomingRuns).not.toHaveBeenCalled();
    });

    it("returns 400 for a non-numeric id", async () => {
        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "not-a-number" }),
        });
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body).toEqual({ error: "Invalid id" });
        expect(mockFindUpcomingRuns).not.toHaveBeenCalled();
    });

    it("returns 500 with rate-limit headers when lookup fails unexpectedly", async () => {
        mockFindUpcomingRuns.mockRejectedValue(new Error("DB unavailable"));

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "123" }),
        });
        const body = await res.json();

        expect(res.status).toBe(500);
        expect(body).toEqual({ error: "Failed to fetch upcoming runs" });
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });
});
