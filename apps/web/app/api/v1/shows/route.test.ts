import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

// Use factory functions so real modules (and their DB deps) are never loaded
vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));
vi.mock("@/lib/data/show/search/getSearchedShows", () => ({
    getSearchedShows: vi.fn(),
}));
// Prevent next-auth (and its next/server import) from loading via the rateLimit chain
vi.mock("@/lib/rateLimit", () => ({
    checkRateLimit: vi.fn(() => ({
        allowed: true,
        limit: 100,
        remaining: 99,
        resetAt: 0,
    })),
    getClientIp: vi.fn(() => "127.0.0.1"),
    RATE_LIMITS: { publicRead: {}, publicReadAuth: {} },
    rateLimitHeaders: vi.fn(() => ({})),
    rateLimitResponse: vi.fn(),
}));

import { GET } from "./route";
import { resolveAuth } from "@/lib/auth/resolveAuth";
import { getSearchedShows } from "@/lib/data/show/search/getSearchedShows";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockGetSearchedShows = vi.mocked(getSearchedShows);

function makeRequest(
    params: Record<string, string> = {},
    { omitZip = false }: { omitZip?: boolean } = {},
): NextRequest {
    const url = new URL("http://localhost/api/v1/shows");
    if (!omitZip) url.searchParams.set("zip", "10001");
    for (const [k, v] of Object.entries(params)) {
        url.searchParams.set(k, v);
    }
    return new NextRequest(url.toString());
}

const mockShowResult = {
    total: 1,
    data: [
        {
            id: "show-1",
            lineup: [{ comedianId: "c1", isFavorite: true }],
        },
    ],
    filters: [],
};

beforeEach(() => {
    vi.clearAllMocks();
});

describe("GET /api/v1/shows", () => {
    describe("authenticated request", () => {
        it("passes profileId and userId to getSearchedShows and returns lineup with isFavorite", async () => {
            const authCtx = { profileId: "profile-abc", userId: "user-abc" };
            mockResolveAuth.mockResolvedValue(authCtx);
            mockGetSearchedShows.mockResolvedValue(mockShowResult as any);

            const req = makeRequest();
            const res = await GET(req);
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(mockGetSearchedShows).toHaveBeenCalledWith(
                expect.objectContaining({
                    profileId: "profile-abc",
                    userId: "user-abc",
                }),
            );
            expect(body.data[0].lineup[0].isFavorite).toBe(true);
        });
    });

    describe("resolveAuth throws", () => {
        it("returns 500 JSON with error key", async () => {
            mockResolveAuth.mockRejectedValue(
                new Error("Token verification failed"),
            );

            const req = makeRequest();
            const res = await GET(req);
            const body = await res.json();

            expect(res.status).toBe(500);
            expect(body).toEqual({ error: "Failed to fetch shows" });
        });
    });

    describe("input validation", () => {
        it("returns 400 when zip is missing", async () => {
            const req = makeRequest({}, { omitZip: true });
            const res = await GET(req);
            const body = await res.json();

            expect(res.status).toBe(400);
            expect(body.error).toMatch(/zip/i);
        });

        it("returns 400 when zip is not a 5-digit code", async () => {
            const req = makeRequest({ zip: "123" });
            const res = await GET(req);
            const body = await res.json();

            expect(res.status).toBe(400);
            expect(body.error).toMatch(/zip/i);
        });

        it("returns 400 when from date is malformed", async () => {
            const req = makeRequest({ from: "not-a-date" });
            const res = await GET(req);
            const body = await res.json();

            expect(res.status).toBe(400);
            expect(body.error).toMatch(/from/i);
        });

        it("returns 400 when from date matches ISO format but is an impossible calendar date", async () => {
            const req = makeRequest({ from: "2024-13-01" });
            const res = await GET(req);
            const body = await res.json();

            expect(res.status).toBe(400);
            expect(body.error).toMatch(/from/i);
        });

        it("returns 400 when to date is malformed", async () => {
            const req = makeRequest({ to: "2024/13/99" });
            const res = await GET(req);
            const body = await res.json();

            expect(res.status).toBe(400);
            expect(body.error).toMatch(/to/i);
        });

        it("returns 400 when to date matches ISO format but is an impossible calendar date", async () => {
            const req = makeRequest({ to: "2024-13-01" });
            const res = await GET(req);
            const body = await res.json();

            expect(res.status).toBe(400);
            expect(body.error).toMatch(/to/i);
        });
    });

    describe("PROFILE_MISSING request", () => {
        it("degrades to anonymous (200, no profileId/userId passed) when resolveAuth returns PROFILE_MISSING", async () => {
            mockResolveAuth.mockResolvedValue("PROFILE_MISSING");
            mockGetSearchedShows.mockResolvedValue(mockShowResult as any);

            const req = makeRequest();
            const res = await GET(req);

            expect(res.status).toBe(200);
            expect(mockGetSearchedShows).toHaveBeenCalledWith(
                expect.not.objectContaining({
                    profileId: expect.anything(),
                    userId: expect.anything(),
                }),
            );
        });
    });

    describe("unauthenticated request", () => {
        it("does not pass profileId/userId and returns results without isFavorite enforced", async () => {
            mockResolveAuth.mockResolvedValue(null);
            const unauthResult = {
                total: 1,
                data: [{ id: "show-1", lineup: [{ comedianId: "c1" }] }],
                filters: [],
            };
            mockGetSearchedShows.mockResolvedValue(unauthResult as any);

            const req = makeRequest();
            const res = await GET(req);
            const body = await res.json();

            expect(res.status).toBe(200);
            // profileId and userId should NOT be passed when unauthenticated
            expect(mockGetSearchedShows).toHaveBeenCalledWith(
                expect.not.objectContaining({
                    profileId: expect.anything(),
                    userId: expect.anything(),
                }),
            );
            expect(body.data[0].lineup[0].isFavorite).toBeUndefined();
        });
    });
});
