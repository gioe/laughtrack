import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";
import { NotFoundError } from "@/objects/NotFoundError";

vi.mock("@/lib/data/podcast/detail/getPodcastEpisodeDetailPageData", () => ({
    getPodcastEpisodeDetailPageData: vi.fn(),
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

import { GET } from "./route";
import { getPodcastEpisodeDetailPageData } from "@/lib/data/podcast/detail/getPodcastEpisodeDetailPageData";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import {
    RATE_LIMIT_SENTINEL_HEADER,
    RATE_LIMIT_SENTINEL_HEADERS,
    RATE_LIMIT_SENTINEL_VALUE,
} from "@/test/rateLimitSentinel";
import { expectOpenApiResponse } from "@/test/openapiResponseValidator";

const mockGetPodcastEpisodeDetailPageData = vi.mocked(
    getPodcastEpisodeDetailPageData,
);
const mockApplyPublicReadRateLimit = vi.mocked(applyPublicReadRateLimit);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

function makeRequest(): NextRequest {
    return new NextRequest("http://localhost/api/v1/podcast-episodes/501");
}

beforeEach(() => {
    vi.clearAllMocks();
    mockApplyPublicReadRateLimit.mockResolvedValue({
        allowed: true,
        limit: 60,
        remaining: 59,
        resetAt: 0,
    });
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
});

describe("GET /api/v1/podcast-episodes/[id]", () => {
    const episodePayload = {
        podcast: {
            id: 42,
            slug: "the-laugh-track-pod",
            title: "The Laugh Track Pod",
            authorName: "Laugh Track Network",
            websiteUrl: "https://podcasts.example.com",
            feedUrl: "https://podcasts.example.com/feed.xml",
            imageUrl: "https://cdn.example.com/podcast.jpg",
            description: "Comedy conversations.",
            episodeCount: 75,
            hosts: [
                {
                    id: 11,
                    uuid: "host-11",
                    name: "Host Comic",
                    imageUrl: "https://cdn.example.com/host.jpg",
                },
            ],
        },
        episode: {
            id: 501,
            title: "Comedy Cellar Stories",
            description: "A set recap.",
            releaseDate: new Date("2026-03-01T00:00:00.000Z"),
            durationSeconds: 3_720,
            episodeUrl: "https://podcasts.example.com/cellar",
            audioUrl: "https://cdn.example.com/cellar.mp3",
            appearances: [
                {
                    id: 101,
                    uuid: "guest-101",
                    name: "Guest Comic",
                    imageUrl: "https://cdn.example.com/guest.jpg",
                },
            ],
        },
    };

    it("returns a first-class episode and its parent podcast context", async () => {
        mockGetPodcastEpisodeDetailPageData.mockResolvedValue(episodePayload);

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "501" }),
        });
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(mockGetPodcastEpisodeDetailPageData).toHaveBeenCalledWith(501);
        expect(body.podcast.title).toBe("The Laugh Track Pod");
        expect(body.podcast.hosts[0].name).toBe("Host Comic");
        expect(body.episode.id).toBe(501);
        expect(body.episode.releaseDate).toBe("2026-03-01T00:00:00.000Z");
        expect(body.episode.durationSeconds).toBe(3_720);
        expect(body.episode.audioUrl).toBe(
            "https://cdn.example.com/cellar.mp3",
        );
        expect(body.episode.appearances[0].name).toBe("Guest Comic");
        expect(body.podcast).not.toHaveProperty("isFavorite");
        expectOpenApiResponse("/podcast-episodes/{id}", 200, body);
    });

    it.each(["501abc", "0", "-1", "9007199254740992"])(
        "returns 400 for invalid id %s without querying",
        async (id) => {
            const res = await GET(makeRequest(), {
                params: Promise.resolve({ id }),
            });

            expect(res.status).toBe(400);
            await expect(res.json()).resolves.toEqual({
                error: "Invalid id",
            });
            expect(mockGetPodcastEpisodeDetailPageData).not.toHaveBeenCalled();
            expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
                RATE_LIMIT_SENTINEL_VALUE,
            );
        },
    );

    it("returns 404 without exposing hidden podcast details", async () => {
        mockGetPodcastEpisodeDetailPageData.mockRejectedValue(
            new NotFoundError(
                "Episode 501 from Hidden Podcast is not publicly visible",
            ),
        );

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "501" }),
        });
        const body = await res.json();

        expect(res.status).toBe(404);
        expect(body).toEqual({ error: "Podcast episode not found" });
        expect(JSON.stringify(body)).not.toContain("Hidden Podcast");
    });

    it("passes through the public-read rate-limit response before validating or querying", async () => {
        mockApplyPublicReadRateLimit.mockResolvedValue(
            NextResponse.json({ error: "Too Many Requests" }, { status: 429 }),
        );

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "invalid" }),
        });

        expect(res.status).toBe(429);
        expect(mockApplyPublicReadRateLimit).toHaveBeenCalledWith(
            expect.any(NextRequest),
            "podcast-episodes-id",
        );
        expect(mockGetPodcastEpisodeDetailPageData).not.toHaveBeenCalled();
    });

    it("adds the standard public-read cache policy and preserves rate-limit headers on success", async () => {
        mockGetPodcastEpisodeDetailPageData.mockResolvedValue(episodePayload);

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "501" }),
        });

        expect(res.status).toBe(200);
        expect(res.headers.get("Cache-Control")).toContain("public");
        expect(res.headers.get("Cache-Control")).toContain("s-maxage");
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });

    it("returns an uncached 500 with rate-limit headers on lookup failure", async () => {
        mockGetPodcastEpisodeDetailPageData.mockRejectedValue(
            new Error("DB unavailable"),
        );

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "501" }),
        });

        expect(res.status).toBe(500);
        await expect(res.json()).resolves.toEqual({
            error: "Failed to fetch podcast episode",
        });
        expect(res.headers.get("Cache-Control")).toBeNull();
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });
});
