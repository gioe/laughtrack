import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { NotFoundError } from "@/objects/NotFoundError";

vi.mock("@/lib/data/podcast/detail/getPodcastDetailPageData", () => ({
    getPodcastDetailPageDataById: vi.fn(),
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
vi.mock("@/lib/auth/resolveAuth", () => ({
    PROFILE_MISSING: Symbol("PROFILE_MISSING"),
    resolveAuth: vi.fn(() => Promise.resolve(null)),
}));

import { GET } from "./route";
import { getPodcastDetailPageDataById } from "@/lib/data/podcast/detail/getPodcastDetailPageData";
import { rateLimitHeaders } from "@/lib/rateLimit";
import { resolveAuth } from "@/lib/auth/resolveAuth";
import {
    RATE_LIMIT_SENTINEL_HEADER,
    RATE_LIMIT_SENTINEL_HEADERS,
    RATE_LIMIT_SENTINEL_VALUE,
} from "@/test/rateLimitSentinel";

const mockGetPodcastDetailPageDataById = vi.mocked(getPodcastDetailPageDataById);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);
const mockResolveAuth = vi.mocked(resolveAuth);

function makeRequest(): NextRequest {
    return new NextRequest("http://localhost/api/v1/podcasts/42");
}

beforeEach(() => {
    vi.clearAllMocks();
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
});

describe("GET /api/v1/podcasts/[id]", () => {
    it("returns podcast detail data by numeric id", async () => {
        mockGetPodcastDetailPageDataById.mockResolvedValue({
            podcast: {
                id: 42,
                slug: "the-laugh-track-pod",
                title: "The Laugh Track Pod",
                authorName: "Laugh Track Network",
                websiteUrl: "https://podcasts.example.com",
                feedUrl: "https://podcasts.example.com/feed.xml",
                imageUrl: "https://cdn.example.com/podcast.jpg",
                description: "Comedy conversations.",
                episodeCount: 12,
            },
            episodes: [
                {
                    id: 501,
                    title: "Comedy Cellar Stories",
                    description: "A set recap.",
                    releaseDate: new Date("2026-03-01T00:00:00.000Z"),
                    durationSeconds: 3_720,
                    episodeUrl: "https://podcasts.example.com/cellar",
                    audioUrl: "https://cdn.example.com/cellar.mp3",
                },
            ],
            relatedComedians: [
                {
                    id: 101,
                    uuid: "demo-comedian-101",
                    name: "Mark Normand",
                    hasImage: false,
                    imageUrl: "",
                    social_data: {
                        id: 101,
                        linktree: null,
                        instagram_account: null,
                        instagram_followers: null,
                        tiktok_account: null,
                        tiktok_followers: null,
                        youtube_account: null,
                        youtube_followers: null,
                        website: null,
                        popularity: null,
                    },
                    bio: null,
                    show_count: 0,
                },
            ],
        });

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "42" }),
        });
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(mockGetPodcastDetailPageDataById).toHaveBeenCalledWith(
            42,
            undefined,
        );
        expect(body.podcast.title).toBe("The Laugh Track Pod");
        expect(body.episodes).toHaveLength(1);
        expect(body.relatedComedians).toHaveLength(1);
    });

    it("passes the authenticated profile id to the detail lookup", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-123",
            userId: "user-123",
            role: "User",
        } as never);
        mockGetPodcastDetailPageDataById.mockResolvedValue({
            podcast: {
                id: 42,
                slug: "the-laugh-track-pod",
                title: "The Laugh Track Pod",
                authorName: "Laugh Track Network",
                websiteUrl: null,
                feedUrl: null,
                imageUrl: null,
                description: null,
                episodeCount: 12,
                isFavorite: true,
            },
            episodes: [],
            relatedComedians: [],
        });

        await GET(makeRequest(), {
            params: Promise.resolve({ id: "42" }),
        });

        expect(mockGetPodcastDetailPageDataById).toHaveBeenCalledWith(
            42,
            "profile-123",
        );
    });

    it("returns 400 for invalid ids", async () => {
        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "42abc" }),
        });

        expect(res.status).toBe(400);
        expect(await res.json()).toEqual({ error: "Invalid id" });
        expect(mockGetPodcastDetailPageDataById).not.toHaveBeenCalled();
    });

    it("returns 404 when the podcast is missing", async () => {
        mockGetPodcastDetailPageDataById.mockRejectedValue(
            new NotFoundError("Podcast not found"),
        );

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "42" }),
        });

        expect(res.status).toBe(404);
        expect(await res.json()).toEqual({ error: "Podcast not found" });
    });

    it("returns 500 when the detail lookup fails unexpectedly", async () => {
        mockGetPodcastDetailPageDataById.mockRejectedValue(
            new Error("DB unavailable"),
        );

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "42" }),
        });

        expect(res.status).toBe(500);
        expect(await res.json()).toEqual({ error: "Failed to fetch podcast" });
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });
});
