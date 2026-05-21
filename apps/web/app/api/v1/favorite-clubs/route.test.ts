import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest, NextResponse } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));
vi.mock("@/lib/db", () => ({
    db: {
        favoriteClub: { findMany: vi.fn() },
        club: { findUnique: vi.fn() },
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
vi.mock("@/util/imageUtil", () => ({
    buildClubImageUrl: vi.fn(
        (name: string, hasImage: boolean) =>
            `https://cdn.test/clubs/${name}.png?hasImage=${hasImage}`,
    ),
}));
vi.mock("@/lib/data/favorites/toggleFavoriteClub", () => ({
    toggleFavoriteClub: vi.fn(() => Promise.resolve(true)),
}));

import { GET, POST } from "./route";
import { resolveAuth } from "@/lib/auth/resolveAuth";
import { db } from "@/lib/db";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { toggleFavoriteClub } from "@/lib/data/favorites/toggleFavoriteClub";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockClubFindUnique = vi.mocked(db.club.findUnique);
const mockFavoriteClubFindMany = vi.mocked(db.favoriteClub.findMany);
const mockApplyPublicReadRateLimit = vi.mocked(applyPublicReadRateLimit);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);
const mockToggleFavoriteClub = vi.mocked(toggleFavoriteClub);

function makeRequest(body: unknown = { clubId: 42 }): NextRequest {
    return new NextRequest("http://localhost/api/v1/favorite-clubs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("/api/v1/favorite-clubs", () => {
    it('invokes applyPublicReadRateLimit with the "favorite-clubs" route prefix for GET', async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFavoriteClubFindMany.mockResolvedValue([]);

        await GET(new NextRequest("http://localhost/api/v1/favorite-clubs"));

        expect(mockApplyPublicReadRateLimit).toHaveBeenCalledWith(
            expect.any(NextRequest),
            "favorite-clubs",
        );
    });

    it("returns the helper's NextResponse from GET when the rate limit is exceeded", async () => {
        const fakeResponse = NextResponse.json(
            { error: "Too Many Requests" },
            { status: 429 },
        );
        mockApplyPublicReadRateLimit.mockResolvedValueOnce(fakeResponse);

        const res = await GET(
            new NextRequest("http://localhost/api/v1/favorite-clubs"),
        );

        expect(res).toBe(fakeResponse);
        expect(mockResolveAuth).not.toHaveBeenCalled();
    });

    it("returns 422 from GET when resolveAuth returns PROFILE_MISSING", async () => {
        mockResolveAuth.mockResolvedValue("PROFILE_MISSING");

        const res = await GET(
            new NextRequest("http://localhost/api/v1/favorite-clubs"),
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
            new NextRequest("http://localhost/api/v1/favorite-clubs"),
        );
        const body = await res.json();

        expect(res.status).toBe(401);
        expect(body.error).toMatch(/authentication required/i);
    });

    it("returns saved favorite clubs from GET in minimal FavoriteClubItem shape", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFavoriteClubFindMany.mockResolvedValue([
            {
                club: {
                    id: 86,
                    name: "Comedy Cellar",
                    hasImage: true,
                },
            },
            {
                club: {
                    id: 42,
                    name: "The Stand",
                    hasImage: false,
                },
            },
        ] as never);

        const res = await GET(
            new NextRequest("http://localhost/api/v1/favorite-clubs"),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(res.headers.get("X-RateLimit-Remaining")).toBe("42");
        expect(mockFavoriteClubFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: { profileId: "profile-1" },
            }),
        );
        expect(body).toEqual({
            data: [
                {
                    id: 86,
                    name: "Comedy Cellar",
                    imageUrl:
                        "https://cdn.test/clubs/Comedy Cellar.png?hasImage=true",
                    isFavorite: true,
                },
                {
                    id: 42,
                    name: "The Stand",
                    imageUrl: "https://cdn.test/clubs/The Stand.png?hasImage=false",
                    isFavorite: true,
                },
            ],
        });
    });

    it('invokes applyPublicReadRateLimit with the "favorite-clubs" route prefix for POST', async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockClubFindUnique.mockResolvedValue({ id: 42 } as never);

        await POST(makeRequest());

        expect(mockApplyPublicReadRateLimit).toHaveBeenCalledWith(
            expect.any(NextRequest),
            "favorite-clubs",
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

    it("returns 400 when clubId is missing or invalid", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });

        const res = await POST(makeRequest({ clubId: "not-a-number" }));
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body.error).toMatch(/clubId/i);
    });

    it("returns 404 when the referenced club does not exist", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockClubFindUnique.mockResolvedValue(null);

        const res = await POST(makeRequest());

        expect(res.status).toBe(404);
        expect(mockToggleFavoriteClub).not.toHaveBeenCalled();
    });

    it("returns 200 with isFavorited:true on success and delegates to toggleFavoriteClub", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockClubFindUnique.mockResolvedValue({ id: 42 } as never);

        const res = await POST(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(res.headers.get("X-RateLimit-Remaining")).toBe("42");
        expect(body).toEqual({ data: { isFavorited: true } });
        expect(mockToggleFavoriteClub).toHaveBeenCalledWith(
            42,
            "profile-1",
            true,
        );
    });
});
