import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest, NextResponse } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));
vi.mock("@/lib/db", () => ({
    db: {
        favoriteComedian: { findMany: vi.fn(), upsert: vi.fn() },
        comedian: { findUnique: vi.fn() },
    },
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

import { GET, POST } from "./route";
import { resolveAuth } from "@/lib/auth/resolveAuth";
import { db } from "@/lib/db";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockFindUnique = vi.mocked(db.comedian.findUnique);
const mockFindMany = vi.mocked(db.favoriteComedian.findMany);
const mockUpsert = vi.mocked(db.favoriteComedian.upsert);
const mockApplyPublicReadRateLimit = vi.mocked(applyPublicReadRateLimit);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

function makeRequest(
    body: unknown = { comedianId: "comedian-uuid-1" },
): NextRequest {
    return new NextRequest("http://localhost/api/v1/favorites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("POST /api/v1/favorites", () => {
    it('invokes applyPublicReadRateLimit with the "favorites" route prefix for GET', async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindMany.mockResolvedValue([]);

        await GET(new NextRequest("http://localhost/api/v1/favorites"));

        expect(mockApplyPublicReadRateLimit).toHaveBeenCalledWith(
            expect.any(NextRequest),
            "favorites",
        );
    });

    it("returns the helper's NextResponse from GET when the rate limit is exceeded", async () => {
        const fakeResponse = NextResponse.json(
            { error: "Too Many Requests" },
            { status: 429 },
        );
        mockApplyPublicReadRateLimit.mockResolvedValueOnce(fakeResponse);

        const res = await GET(
            new NextRequest("http://localhost/api/v1/favorites"),
        );

        expect(res).toBe(fakeResponse);
        expect(mockResolveAuth).not.toHaveBeenCalled();
    });

    it("returns 422 from GET when resolveAuth returns PROFILE_MISSING", async () => {
        mockResolveAuth.mockResolvedValue("PROFILE_MISSING");

        const res = await GET(
            new NextRequest("http://localhost/api/v1/favorites"),
        );
        const body = await res.json();

        expect(res.status).toBe(422);
        expect(body.error).toMatch(/profile not found/i);
        expect(mockRateLimitHeaders).toHaveBeenCalled();
        expect(res.headers.get("X-RateLimit-Remaining")).toBe("42");
    });

    it("returns 401 from GET when resolveAuth returns null", async () => {
        mockResolveAuth.mockResolvedValue(null);

        const res = await GET(
            new NextRequest("http://localhost/api/v1/favorites"),
        );
        const body = await res.json();

        expect(res.status).toBe(401);
        expect(body.error).toMatch(/authentication required/i);
    });

    it("returns saved favorites from GET for the authenticated profile", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindMany.mockResolvedValue([
            {
                comedian: {
                    id: 101,
                    uuid: "comedian-uuid-1",
                    name: "Taylor Tomlinson",
                    instagramAccount: "taylortomlinson",
                    instagramFollowers: 100,
                    tiktokAccount: null,
                    tiktokFollowers: null,
                    youtubeAccount: null,
                    youtubeFollowers: null,
                    website: "https://example.com/taylor",
                    popularity: 42,
                    linktree: null,
                    hasImage: true,
                    _count: { lineupItems: 5 },
                },
            },
        ] as any);

        const res = await GET(
            new NextRequest("http://localhost/api/v1/favorites"),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(res.headers.get("X-RateLimit-Remaining")).toBe("42");
        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: { profileId: "profile-1" },
            }),
        );
        expect(body).toEqual({
            data: [
                {
                    id: 101,
                    uuid: "comedian-uuid-1",
                    name: "Taylor Tomlinson",
                    imageUrl:
                        "https://test.b-cdn.net/comedians/Taylor%20Tomlinson.png",
                    social_data: {
                        id: 101,
                        instagram_account: "taylortomlinson",
                        instagram_followers: 100,
                        tiktok_account: null,
                        tiktok_followers: null,
                        youtube_account: null,
                        youtube_followers: null,
                        website: "https://example.com/taylor",
                        popularity: 42,
                        linktree: null,
                    },
                    show_count: 5,
                    isFavorite: true,
                },
            ],
        });
    });

    it('invokes applyPublicReadRateLimit with the "favorites" route prefix for POST', async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindUnique.mockResolvedValue({ uuid: "comedian-uuid-1" } as any);
        mockUpsert.mockResolvedValue({} as any);

        await POST(makeRequest());

        expect(mockApplyPublicReadRateLimit).toHaveBeenCalledWith(
            expect.any(NextRequest),
            "favorites",
        );
    });

    it("returns the helper's NextResponse from POST when the rate limit is exceeded", async () => {
        const fakeResponse = NextResponse.json(
            { error: "Too Many Requests" },
            { status: 429 },
        );
        mockApplyPublicReadRateLimit.mockResolvedValueOnce(fakeResponse);

        const res = await POST(makeRequest());

        expect(res).toBe(fakeResponse);
        expect(mockResolveAuth).not.toHaveBeenCalled();
    });

    it("returns 422 when resolveAuth returns PROFILE_MISSING", async () => {
        mockResolveAuth.mockResolvedValue("PROFILE_MISSING");

        const res = await POST(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(422);
        expect(body.error).toMatch(/profile not found/i);
        expect(res.headers.get("X-RateLimit-Remaining")).toBe("42");
    });

    it("returns 401 when resolveAuth returns null", async () => {
        mockResolveAuth.mockResolvedValue(null);

        const res = await POST(makeRequest());

        expect(res.status).toBe(401);
    });

    it("returns 200 with isFavorited:true on success", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindUnique.mockResolvedValue({ uuid: "comedian-uuid-1" } as any);
        mockUpsert.mockResolvedValue({} as any);

        const res = await POST(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(res.headers.get("X-RateLimit-Remaining")).toBe("42");
        expect(body).toEqual({ data: { isFavorited: true } });
    });
});
