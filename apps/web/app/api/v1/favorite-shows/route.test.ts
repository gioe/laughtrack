import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest, NextResponse } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));
vi.mock("@/lib/db", () => ({
    db: {
        show: { count: vi.fn() },
    },
}));
vi.mock("@/lib/data/home/findShowsForHome", () => ({
    findShowsForHome: vi.fn(),
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
    rateLimitHeaders: vi.fn(() => ({ "X-RateLimit-Remaining": "42" })),
}));

import { GET } from "./route";
import { resolveAuth } from "@/lib/auth/resolveAuth";
import { db } from "@/lib/db";
import { findShowsForHome } from "@/lib/data/home/findShowsForHome";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockCount = vi.mocked(db.show.count);
const mockFindShowsForHome = vi.mocked(findShowsForHome);
const mockApplyPublicReadRateLimit = vi.mocked(applyPublicReadRateLimit);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

beforeEach(() => {
    vi.clearAllMocks();
});

describe("GET /api/v1/favorite-shows", () => {
    it('invokes applyPublicReadRateLimit with the "favorite-shows" route prefix', async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockCount.mockResolvedValue(0);
        mockFindShowsForHome.mockResolvedValue([]);

        await GET(new NextRequest("http://localhost/api/v1/favorite-shows"));

        expect(mockApplyPublicReadRateLimit).toHaveBeenCalledWith(
            expect.any(NextRequest),
            "favorite-shows",
        );
    });

    it("returns the helper's NextResponse when the rate limit is exceeded", async () => {
        const fakeResponse = NextResponse.json(
            { error: "Too Many Requests" },
            { status: 429 },
        );
        mockApplyPublicReadRateLimit.mockResolvedValueOnce(fakeResponse);

        const res = await GET(
            new NextRequest("http://localhost/api/v1/favorite-shows"),
        );

        expect(res).toBe(fakeResponse);
        expect(mockResolveAuth).not.toHaveBeenCalled();
    });

    it("returns 422 when resolveAuth returns PROFILE_MISSING", async () => {
        mockResolveAuth.mockResolvedValue("PROFILE_MISSING");

        const res = await GET(
            new NextRequest("http://localhost/api/v1/favorite-shows"),
        );
        const body = await res.json();

        expect(res.status).toBe(422);
        expect(body.error).toMatch(/profile not found/i);
        expect(mockRateLimitHeaders).toHaveBeenCalled();
        expect(res.headers.get("X-RateLimit-Remaining")).toBe("42");
    });

    it("returns 401 when resolveAuth returns null", async () => {
        mockResolveAuth.mockResolvedValue(null);

        const res = await GET(
            new NextRequest("http://localhost/api/v1/favorite-shows"),
        );
        const body = await res.json();

        expect(res.status).toBe(401);
        expect(body.error).toMatch(/authentication required/i);
    });

    it("queries upcoming shows whose lineup contains the user's favorited comedians", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-99",
            userId: "user-1",
        });
        mockCount.mockResolvedValue(0);
        mockFindShowsForHome.mockResolvedValue([]);

        await GET(new NextRequest("http://localhost/api/v1/favorite-shows"));

        const where = mockCount.mock.calls[0][0]?.where as Record<
            string,
            unknown
        >;
        expect(where).toBeDefined();
        expect(where.club).toEqual({ visible: true });
        expect(where.lineupItems).toEqual({
            some: {
                comedian: {
                    favoriteComedians: {
                        some: { profileId: "profile-99" },
                    },
                },
            },
        });
        const dateFilter = where.date as { gte: Date };
        expect(dateFilter.gte).toBeInstanceOf(Date);
    });

    it("returns paginated shows with total + page + size + totalPages", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockCount.mockResolvedValue(45);
        mockFindShowsForHome.mockResolvedValue([
            { id: 1 } as never,
            { id: 2 } as never,
        ]);

        const res = await GET(
            new NextRequest(
                "http://localhost/api/v1/favorite-shows?page=2&size=20",
            ),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.data).toEqual([{ id: 1 }, { id: 2 }]);
        expect(body.total).toBe(45);
        expect(body.page).toBe(2);
        expect(body.size).toBe(20);
        expect(body.totalPages).toBe(3);
        expect(mockFindShowsForHome).toHaveBeenCalledWith(
            expect.any(Object),
            [{ date: "asc" }, { popularity: "desc" }],
            20,
            {},
            20,
        );
    });

    it("clamps size to MAX_PAGE_SIZE (50)", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockCount.mockResolvedValue(0);
        mockFindShowsForHome.mockResolvedValue([]);

        await GET(
            new NextRequest(
                "http://localhost/api/v1/favorite-shows?size=9999",
            ),
        );

        expect(mockFindShowsForHome).toHaveBeenCalledWith(
            expect.any(Object),
            expect.any(Array),
            50,
            {},
            0,
        );
    });

    it("falls back to defaults when page or size are non-positive or unparseable", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockCount.mockResolvedValue(0);
        mockFindShowsForHome.mockResolvedValue([]);

        const res = await GET(
            new NextRequest(
                "http://localhost/api/v1/favorite-shows?page=-1&size=abc",
            ),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.page).toBe(1);
        expect(body.size).toBe(20);
    });

    it("returns totalPages of 1 when total is 0", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockCount.mockResolvedValue(0);
        mockFindShowsForHome.mockResolvedValue([]);

        const res = await GET(
            new NextRequest("http://localhost/api/v1/favorite-shows"),
        );
        const body = await res.json();

        expect(body.total).toBe(0);
        expect(body.totalPages).toBe(1);
    });
});
