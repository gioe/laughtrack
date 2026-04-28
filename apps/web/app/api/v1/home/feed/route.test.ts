import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest, NextResponse } from "next/server";

vi.mock("@/auth", () => ({
    auth: vi.fn(),
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
    rateLimitHeaders: vi.fn(() => ({})),
}));
vi.mock("@/lib/data/home/getHeroContext", () => ({
    getHeroContext: vi.fn(),
}));
vi.mock("@/lib/data/home/getTrendingComedians", () => ({
    getTrendingComedians: vi.fn(),
}));
vi.mock("@/lib/data/home/getClubs", () => ({
    getClubs: vi.fn(),
}));
vi.mock("@/lib/data/home/getComediansByZip", () => ({
    getComediansByZip: vi.fn(),
}));
vi.mock("@/lib/data/home/getShowsTonight", () => ({
    getShowsTonight: vi.fn(),
}));
vi.mock("@/lib/data/home/getShowsNearZip", () => ({
    getShowsNearZip: vi.fn(),
}));
vi.mock("@/lib/data/home/getTrendingShowsThisWeek", () => ({
    getTrendingShowsThisWeek: vi.fn(),
}));

import { GET } from "./route";
import { auth } from "@/auth";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { getHeroContext } from "@/lib/data/home/getHeroContext";
import { getTrendingComedians } from "@/lib/data/home/getTrendingComedians";
import { getClubs } from "@/lib/data/home/getClubs";
import { getComediansByZip } from "@/lib/data/home/getComediansByZip";
import { getShowsTonight } from "@/lib/data/home/getShowsTonight";
import { getShowsNearZip } from "@/lib/data/home/getShowsNearZip";
import { getTrendingShowsThisWeek } from "@/lib/data/home/getTrendingShowsThisWeek";

const mockAuth = vi.mocked(auth);
const mockApplyPublicReadRateLimit = vi.mocked(applyPublicReadRateLimit);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);
const mockGetHeroContext = vi.mocked(getHeroContext);
const mockGetTrendingComedians = vi.mocked(getTrendingComedians);
const mockGetClubs = vi.mocked(getClubs);
const mockGetComediansByZip = vi.mocked(getComediansByZip);
const mockGetShowsTonight = vi.mocked(getShowsTonight);
const mockGetShowsNearZip = vi.mocked(getShowsNearZip);
const mockGetTrendingShowsThisWeek = vi.mocked(getTrendingShowsThisWeek);

function makeRequest(
    params: Record<string, string> = {},
    headers: Record<string, string> = {},
): NextRequest {
    const url = new URL("http://localhost/api/v1/home/feed");
    for (const [k, v] of Object.entries(params)) {
        url.searchParams.set(k, v);
    }
    return new NextRequest(url.toString(), { headers });
}

function primeHappyPath() {
    mockGetTrendingComedians.mockResolvedValue([]);
    mockGetClubs.mockResolvedValue([]);
    mockGetComediansByZip.mockResolvedValue([]);
    mockGetShowsTonight.mockResolvedValue([]);
    mockGetShowsNearZip.mockResolvedValue([]);
    mockGetTrendingShowsThisWeek.mockResolvedValue([]);
}

beforeEach(() => {
    vi.clearAllMocks();
    mockAuth.mockResolvedValue(null as any);
    mockGetHeroContext.mockResolvedValue({
        zipCode: null,
        city: null,
        state: null,
    });
    primeHappyPath();
});

describe("GET /api/v1/home/feed", () => {
    describe("zip validation", () => {
        it("returns 400 when zip is not a 5-digit code", async () => {
            const res = await GET(makeRequest({ zip: "abc" }));
            const body = await res.json();

            expect(res.status).toBe(400);
            expect(body.error).toMatch(/zip/i);
            expect(mockGetHeroContext).not.toHaveBeenCalled();
        });

        it("attaches rateLimitHeaders to the 400 response", async () => {
            mockRateLimitHeaders.mockReturnValueOnce({
                "X-RateLimit-Remaining": "42",
            });

            const res = await GET(makeRequest({ zip: "abc" }));

            expect(res.status).toBe(400);
            expect(mockRateLimitHeaders).toHaveBeenCalled();
            expect(res.headers.get("X-RateLimit-Remaining")).toBe("42");
        });

        it("accepts a valid 5-digit zip", async () => {
            mockGetHeroContext.mockResolvedValue({
                zipCode: "10001",
                city: "New York",
                state: "NY",
            });

            const res = await GET(makeRequest({ zip: "10001" }));

            expect(res.status).toBe(200);
            expect(mockGetHeroContext).toHaveBeenCalledWith("10001");
        });
    });

    describe("zipCode resolution precedence", () => {
        it("passes ?zip= to getHeroContext when query param is set (overrides session zip)", async () => {
            mockAuth.mockResolvedValue({
                profile: { zipCode: "90210", userid: "user-1" },
            } as any);

            await GET(makeRequest({ zip: "10001" }));

            expect(mockGetHeroContext).toHaveBeenCalledWith("10001");
        });

        it("falls back to session profile zipCode when ?zip is absent", async () => {
            mockAuth.mockResolvedValue({
                profile: { zipCode: "90210", userid: "user-1" },
            } as any);

            await GET(makeRequest());

            expect(mockGetHeroContext).toHaveBeenCalledWith("90210");
        });

        it("passes null to getHeroContext when neither ?zip nor session zip exist", async () => {
            await GET(makeRequest());

            expect(mockGetHeroContext).toHaveBeenCalledWith(null);
        });
    });

    describe("null zipCode path", () => {
        it("skips zip-based fetches and returns empty near-you sections", async () => {
            // getHeroContext already returns { zipCode: null } from beforeEach
            const res = await GET(makeRequest());
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(mockGetComediansByZip).not.toHaveBeenCalled();
            expect(mockGetShowsNearZip).not.toHaveBeenCalled();
            expect(body.data.comediansNearYou).toEqual([]);
            expect(body.data.moreNearYou).toEqual([]);
            expect(body.data.hero.shows).toEqual([]);
        });
    });

    describe("hero.shows slicing", () => {
        it("puts the first 3 showsNearZip into hero.shows and the rest into moreNearYou", async () => {
            mockGetHeroContext.mockResolvedValue({
                zipCode: "10001",
                city: "New York",
                state: "NY",
            });
            mockGetShowsNearZip.mockResolvedValue([
                { id: 1 },
                { id: 2 },
                { id: 3 },
                { id: 4 },
                { id: 5 },
            ] as any);

            const res = await GET(makeRequest({ zip: "10001" }));
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(
                body.data.hero.shows.map((s: { id: number }) => s.id),
            ).toEqual([1, 2, 3]);
            expect(
                body.data.moreNearYou.map((s: { id: number }) => s.id),
            ).toEqual([4, 5]);
        });

        it("returns empty moreNearYou when fewer than 3 near-you shows exist", async () => {
            mockGetHeroContext.mockResolvedValue({
                zipCode: "10001",
                city: "New York",
                state: "NY",
            });
            mockGetShowsNearZip.mockResolvedValue([
                { id: 1 },
                { id: 2 },
            ] as any);

            const res = await GET(makeRequest({ zip: "10001" }));
            const body = await res.json();

            expect(
                body.data.hero.shows.map((s: { id: number }) => s.id),
            ).toEqual([1, 2]);
            expect(body.data.moreNearYou).toEqual([]);
        });
    });

    describe("getHeroContext rejection", () => {
        it("falls back to a null hero and still returns 200", async () => {
            mockGetHeroContext.mockRejectedValueOnce(new Error("hero boom"));

            const res = await GET(makeRequest());
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(body.data.hero).toEqual({
                zipCode: null,
                city: null,
                state: null,
                shows: [],
            });
            expect(body.data.comediansNearYou).toEqual([]);
            expect(body.data.moreNearYou).toEqual([]);
        });
    });

    describe("per-section failure isolation", () => {
        it("returns 200 with empty arrays for sections whose helper rejects", async () => {
            mockGetHeroContext.mockResolvedValue({
                zipCode: "10001",
                city: "New York",
                state: "NY",
            });
            mockGetComediansByZip.mockRejectedValue(new Error("boom"));
            mockGetShowsNearZip.mockRejectedValue(new Error("boom"));
            mockGetTrendingComedians.mockRejectedValue(new Error("boom"));

            const res = await GET(makeRequest({ zip: "10001" }));
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(body.data.comediansNearYou).toEqual([]);
            expect(body.data.moreNearYou).toEqual([]);
            expect(body.data.trendingComedians).toEqual([]);
        });
    });

    describe("cache headers", () => {
        it("emits Cache-Control: private on the 200 response", async () => {
            const res = await GET(makeRequest());

            expect(res.status).toBe(200);
            expect(res.headers.get("Cache-Control")).toContain("private");
        });
    });

    describe("X-Timezone forwarding", () => {
        it("forwards the X-Timezone header to getShowsTonight and getTrendingShowsThisWeek", async () => {
            await GET(makeRequest({}, { "X-Timezone": "America/Los_Angeles" }));

            expect(mockGetShowsTonight).toHaveBeenCalledWith(
                "America/Los_Angeles",
            );
            expect(mockGetTrendingShowsThisWeek).toHaveBeenCalledWith(
                "America/Los_Angeles",
            );
        });

        it("defaults to UTC when X-Timezone is absent", async () => {
            await GET(makeRequest());

            expect(mockGetShowsTonight).toHaveBeenCalledWith("UTC");
            expect(mockGetTrendingShowsThisWeek).toHaveBeenCalledWith("UTC");
        });

        it("returns 400 when X-Timezone is not a valid IANA zone", async () => {
            const res = await GET(
                makeRequest({}, { "X-Timezone": "Not/Real" }),
            );
            const body = await res.json();

            expect(res.status).toBe(400);
            expect(body.error).toMatch(/X-Timezone/);
            expect(mockGetShowsTonight).not.toHaveBeenCalled();
            expect(mockGetTrendingShowsThisWeek).not.toHaveBeenCalled();
        });
    });

    describe("rate limiting", () => {
        it("returns the helper's NextResponse when the rate limit is exceeded", async () => {
            const fakeResponse = NextResponse.json(
                { error: "Too Many Requests" },
                { status: 429 },
            );
            mockApplyPublicReadRateLimit.mockResolvedValueOnce(fakeResponse);

            const res = await GET(makeRequest());

            expect(res).toBe(fakeResponse);
            expect(mockGetHeroContext).not.toHaveBeenCalled();
        });

        it('invokes applyPublicReadRateLimit with the "home" route prefix', async () => {
            await GET(makeRequest());

            expect(mockApplyPublicReadRateLimit).toHaveBeenCalledWith(
                expect.any(NextRequest),
                "home",
            );
        });
    });
});
