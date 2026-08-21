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
        $queryRaw: vi.fn(),
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
const mockQueryRaw = vi.mocked(db.$queryRaw);
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
    mockQueryRaw.mockResolvedValue([]);
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

    it("marks the user-scoped GET 200 response no-store so private favorites never enter a shared cache", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindMany.mockResolvedValue([]);

        const res = await GET(
            new NextRequest("http://localhost/api/v1/favorites"),
        );

        expect(res.status).toBe(200);
        const cacheControl = res.headers.get("Cache-Control");
        expect(cacheControl).toContain("no-store");
        expect(cacheControl).toContain("private");
        // Must never be shared-cacheable — no public directive, no shared TTL.
        expect(cacheControl).not.toContain("public");
        expect(cacheControl).not.toContain("s-maxage");
        // Rate-limit headers still survive the merge.
        expect(res.headers.get("X-RateLimit-Remaining")).toBe("42");
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
                },
            },
        ] as never);
        mockQueryRaw.mockResolvedValue([
            { favorite_id: 101, show_count: BigInt(5) },
        ]);

        const res = await GET(
            new NextRequest("http://localhost/api/v1/favorites"),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(res.headers.get("X-RateLimit-Remaining")).toBe("42");
        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    profileId: "profile-1",
                    comedian: { visible: true },
                },
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
                    socialData: {
                        id: 101,
                        instagramAccount: "taylortomlinson",
                        instagramFollowers: 100,
                        tiktokAccount: null,
                        tiktokFollowers: null,
                        youtubeAccount: null,
                        youtubeFollowers: null,
                        website: "https://example.com/taylor",
                        popularity: 42,
                        linktree: null,
                    },
                    showCount: 5,
                    isFavorite: true,
                },
            ],
        });
    });

    it("counts each show once across the full canonical descendant family", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindMany.mockResolvedValue([
            {
                comedian: {
                    id: 854864,
                    uuid: "jesus-root",
                    name: "Jesús Sepúlveda",
                    instagramAccount: null,
                    instagramFollowers: null,
                    tiktokAccount: null,
                    tiktokFollowers: null,
                    youtubeAccount: null,
                    youtubeFollowers: null,
                    website: null,
                    popularity: 0,
                    linktree: null,
                    hasImage: false,
                    imageAssets: [],
                },
            },
        ] as never);
        mockQueryRaw.mockResolvedValue([
            { favorite_id: 854864, show_count: BigInt(1) },
        ]);

        const res = await GET(
            new NextRequest("http://localhost/api/v1/favorites"),
        );
        const body = await res.json();

        expect(mockQueryRaw).toHaveBeenCalledOnce();
        const query = mockQueryRaw.mock.calls[0][0] as unknown as {
            strings: string[];
            values: unknown[];
        };
        const sql = query.strings.join("?");
        expect(sql).toContain("WITH RECURSIVE favorite_ancestors");
        expect(sql).toContain("child.parent_comedian_id = members.member_id");
        expect(sql).toContain("li.comedian_id = members.member_uuid");
        expect(sql).toContain("COUNT(DISTINCT li.show_id)");
        expect(query.values).toContain(854864);
        expect(body.data[0].showCount).toBe(1);
    });

    it('invokes applyPublicReadRateLimit with the "favorites" route prefix for POST', async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindUnique.mockResolvedValue({ uuid: "comedian-uuid-1" } as never);
        mockUpsert.mockResolvedValue({} as never);

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
        mockFindUnique.mockResolvedValue({
            uuid: "comedian-uuid-1",
            visible: true,
        } as never);
        mockUpsert.mockResolvedValue({} as never);

        const res = await POST(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(res.headers.get("X-RateLimit-Remaining")).toBe("42");
        expect(body).toEqual({ data: { isFavorited: true } });
    });

    it("returns 404 when the requested comedian is hidden (visible=false)", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindUnique.mockResolvedValue({
            uuid: "comedian-uuid-1",
            visible: false,
        } as never);

        const res = await POST(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(404);
        expect(body.error).toMatch(/not found/i);
        expect(mockUpsert).not.toHaveBeenCalled();
    });
});
