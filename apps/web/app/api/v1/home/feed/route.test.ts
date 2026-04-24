import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));
vi.mock("@/lib/rateLimit", () => ({
    checkRateLimit: vi.fn(() =>
        Promise.resolve({
            allowed: true,
            limit: 100,
            remaining: 99,
            resetAt: 0,
        }),
    ),
    getClientIp: vi.fn(() => "127.0.0.1"),
    RATE_LIMITS: { publicRead: {}, publicReadAuth: {} },
    rateLimitHeaders: vi.fn(() => ({})),
    rateLimitResponse: vi.fn(),
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
import { getHeroContext } from "@/lib/data/home/getHeroContext";
import { getTrendingComedians } from "@/lib/data/home/getTrendingComedians";
import { getClubs } from "@/lib/data/home/getClubs";
import { getComediansByZip } from "@/lib/data/home/getComediansByZip";
import { getShowsTonight } from "@/lib/data/home/getShowsTonight";
import { getShowsNearZip } from "@/lib/data/home/getShowsNearZip";
import { getTrendingShowsThisWeek } from "@/lib/data/home/getTrendingShowsThisWeek";

const mockAuth = vi.mocked(auth);
const mockGetHeroContext = vi.mocked(getHeroContext);
const mockGetTrendingComedians = vi.mocked(getTrendingComedians);
const mockGetClubs = vi.mocked(getClubs);
const mockGetComediansByZip = vi.mocked(getComediansByZip);
const mockGetShowsTonight = vi.mocked(getShowsTonight);
const mockGetShowsNearZip = vi.mocked(getShowsNearZip);
const mockGetTrendingShowsThisWeek = vi.mocked(getTrendingShowsThisWeek);

function makeRequest(params: Record<string, string> = {}): NextRequest {
    const url = new URL("http://localhost/api/v1/home/feed");
    for (const [k, v] of Object.entries(params)) {
        url.searchParams.set(k, v);
    }
    return new NextRequest(url.toString());
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
});
