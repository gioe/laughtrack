import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

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

import { GET, POST } from "./route";
import { resolveAuth } from "@/lib/auth/resolveAuth";
import { db } from "@/lib/db";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockFindUnique = vi.mocked(db.comedian.findUnique);
const mockFindMany = vi.mocked(db.favoriteComedian.findMany);
const mockUpsert = vi.mocked(db.favoriteComedian.upsert);

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
    it("returns 422 from GET when resolveAuth returns PROFILE_MISSING", async () => {
        mockResolveAuth.mockResolvedValue("PROFILE_MISSING");

        const res = await GET(new NextRequest("http://localhost/api/v1/favorites"));
        const body = await res.json();

        expect(res.status).toBe(422);
        expect(body.error).toMatch(/profile not found/i);
    });

    it("returns 401 from GET when resolveAuth returns null", async () => {
        mockResolveAuth.mockResolvedValue(null);

        const res = await GET(new NextRequest("http://localhost/api/v1/favorites"));
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

        const res = await GET(new NextRequest("http://localhost/api/v1/favorites"));
        const body = await res.json();

        expect(res.status).toBe(200);
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

    it("returns 422 when resolveAuth returns PROFILE_MISSING", async () => {
        mockResolveAuth.mockResolvedValue("PROFILE_MISSING");

        const res = await POST(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(422);
        expect(body.error).toMatch(/profile not found/i);
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
        expect(body).toEqual({ data: { isFavorited: true } });
    });
});
