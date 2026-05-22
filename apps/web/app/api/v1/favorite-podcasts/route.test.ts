import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest, NextResponse } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));
vi.mock("@/lib/db", () => ({
    db: {
        favoritePodcast: { findMany: vi.fn(), upsert: vi.fn() },
        podcast: { findUnique: vi.fn() },
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
const mockFindUnique = vi.mocked(db.podcast.findUnique);
const mockFindMany = vi.mocked(db.favoritePodcast.findMany);
const mockUpsert = vi.mocked(db.favoritePodcast.upsert);
const mockApplyPublicReadRateLimit = vi.mocked(applyPublicReadRateLimit);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

function makeRequest(body: unknown = { podcastId: 42 }): NextRequest {
    return new NextRequest("http://localhost/api/v1/favorite-podcasts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("/api/v1/favorite-podcasts", () => {
    it('invokes applyPublicReadRateLimit with the "favorite-podcasts" route prefix for GET', async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindMany.mockResolvedValue([]);

        await GET(new NextRequest("http://localhost/api/v1/favorite-podcasts"));

        expect(mockApplyPublicReadRateLimit).toHaveBeenCalledWith(
            expect.any(NextRequest),
            "favorite-podcasts",
        );
    });

    it("returns the helper's NextResponse from GET when the rate limit is exceeded", async () => {
        const fakeResponse = NextResponse.json(
            { error: "Too Many Requests" },
            { status: 429 },
        );
        mockApplyPublicReadRateLimit.mockResolvedValueOnce(fakeResponse);

        const res = await GET(
            new NextRequest("http://localhost/api/v1/favorite-podcasts"),
        );

        expect(res).toBe(fakeResponse);
        expect(mockResolveAuth).not.toHaveBeenCalled();
    });

    it("returns 422 from GET when resolveAuth returns PROFILE_MISSING", async () => {
        mockResolveAuth.mockResolvedValue("PROFILE_MISSING");

        const res = await GET(
            new NextRequest("http://localhost/api/v1/favorite-podcasts"),
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
            new NextRequest("http://localhost/api/v1/favorite-podcasts"),
        );
        const body = await res.json();

        expect(res.status).toBe(401);
        expect(body.error).toMatch(/authentication required/i);
    });

    it("returns saved favorite podcasts from GET for the authenticated profile", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindMany.mockResolvedValue([
            {
                podcast: {
                    id: 42,
                    slug: "the-laugh-track-pod",
                    title: "The Laugh Track Pod",
                    authorName: "Host McHost",
                    websiteUrl: "https://example.com/pod",
                    feedUrl: "https://example.com/pod/rss.xml",
                    imageUrl: "https://example.com/pod/art.jpg",
                    description: "Comedy interviews.",
                    _count: { episodes: 12 },
                },
            },
        ] as never);

        const res = await GET(
            new NextRequest("http://localhost/api/v1/favorite-podcasts"),
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
                    id: 42,
                    slug: "the-laugh-track-pod",
                    title: "The Laugh Track Pod",
                    author_name: "Host McHost",
                    website_url: "https://example.com/pod",
                    feed_url: "https://example.com/pod/rss.xml",
                    image_url: "https://example.com/pod/art.jpg",
                    description: "Comedy interviews.",
                    episode_count: 12,
                    isFavorite: true,
                },
            ],
        });
    });

    it('invokes applyPublicReadRateLimit with the "favorite-podcasts" route prefix for POST', async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindUnique.mockResolvedValue({ id: 42 } as never);
        mockUpsert.mockResolvedValue({} as never);

        await POST(makeRequest());

        expect(mockApplyPublicReadRateLimit).toHaveBeenCalledWith(
            expect.any(NextRequest),
            "favorite-podcasts",
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

    it("returns 400 when podcastId is missing or invalid", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });

        const res = await POST(makeRequest({ podcastId: "not-a-number" }));
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body.error).toMatch(/podcastId/i);
    });

    it("returns 404 when the referenced podcast does not exist", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindUnique.mockResolvedValue(null);

        const res = await POST(makeRequest());

        expect(res.status).toBe(404);
    });

    it("returns 200 with isFavorited:true on success", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindUnique.mockResolvedValue({ id: 42 } as never);
        mockUpsert.mockResolvedValue({} as never);

        const res = await POST(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(res.headers.get("X-RateLimit-Remaining")).toBe("42");
        expect(body).toEqual({ data: { isFavorited: true } });
        expect(mockUpsert).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    profileId_podcastId: {
                        profileId: "profile-1",
                        podcastId: 42,
                    },
                },
                create: { profileId: "profile-1", podcastId: 42 },
                update: {},
            }),
        );
    });
});
