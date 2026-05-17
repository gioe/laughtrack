import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

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
vi.mock("@/lib/db", () => ({
    db: {
        comedian: {
            findUnique: vi.fn(),
        },
    },
}));
vi.mock("@/util/imageUtil", () => ({
    buildComedianImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.jpg`,
    ),
}));

import { GET } from "./route";
import { db } from "@/lib/db";
import { rateLimitHeaders } from "@/lib/rateLimit";
import {
    RATE_LIMIT_SENTINEL_HEADER,
    RATE_LIMIT_SENTINEL_HEADERS,
    RATE_LIMIT_SENTINEL_VALUE,
} from "@/test/rateLimitSentinel";
import { expectOpenApiResponse } from "@/test/openapiResponseValidator";
import { defaultComedianWebsiteHealthFields } from "@/test/comedianFixtures";

const mockFindUnique = vi.mocked(db.comedian.findUnique);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

function makeRequest(): NextRequest {
    return new NextRequest("http://localhost/api/v1/comedians/226475");
}

beforeEach(() => {
    vi.clearAllMocks();
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
});

describe("GET /api/v1/comedians/[id]", () => {
    it("returns comedian detail social data with id for the iOS OpenAPI contract", async () => {
        mockFindUnique.mockResolvedValue({
            id: 226475,
            uuid: "comedian-uuid",
            name: "Marcus D. Wiley",
            totalShows: 0,
            soldOutShows: 0,
            linktree: null,
            songkickId: null,
            bandsintownId: null,
            instagramAccount: null,
            instagramFollowers: null,
            tiktokAccount: null,
            tiktokFollowers: null,
            youtubeAccount: null,
            youtubeFollowers: null,
            website: "https://marcusdwiley.com/",
            websiteDiscoverySource: null,
            websiteLastScraped: null,
            websiteScrapeStrategy: null,
            websiteScrapingUrl: null,
            websiteConfidence: null,
            websiteScrapingUrlConfidence: null,
            ...defaultComedianWebsiteHealthFields,
            popularity: 0.6,
            hasImage: false,
            bio: null,
            parentComedianId: null,
            tourSourceReviewEvidence: null,
            episodeAppearances: [],
        } as never);

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "226475" }),
        });
        const body = await res.json();

        expect(res.status).toBe(200);
        expectOpenApiResponse("/comedians/{id}", 200, body);
        expect(body.data.social_data).toMatchObject({
            id: 226475,
            website: "https://marcusdwiley.com/",
            popularity: 0.6,
        });
    });

    it("returns podcast appearance episode DTOs for the iOS OpenAPI contract", async () => {
        mockFindUnique.mockResolvedValue({
            id: 226475,
            uuid: "comedian-uuid",
            name: "Marcus D. Wiley",
            linktree: null,
            instagramAccount: null,
            instagramFollowers: null,
            tiktokAccount: null,
            tiktokFollowers: null,
            youtubeAccount: null,
            youtubeFollowers: null,
            website: "https://marcusdwiley.com/",
            popularity: 0.6,
            hasImage: true,
            episodeAppearances: [
                {
                    id: 91,
                    appearanceRole: "guest",
                    episode: {
                        id: 17,
                        source: "podcast_index",
                        sourceEpisodeId: "episode-17",
                        title: "Road Stories",
                        releaseDate: new Date("2026-05-01T12:00:00.000Z"),
                        durationSeconds: 1840,
                        episodeUrl: "https://pod.example.com/episodes/17",
                        audioUrl: "https://cdn.example.com/episodes/17.mp3",
                        podcast: {
                            id: 6,
                            source: "podcast_index",
                            sourcePodcastId: "feed-6",
                            title: "The Green Room",
                            imageUrl: "https://cdn.example.com/podcast.jpg",
                            websiteUrl: "https://pod.example.com",
                            feedUrl: "https://pod.example.com/feed.xml",
                            authorName: "Green Room Network",
                        },
                        appearances: [
                            {
                                id: 90,
                                appearanceRole: "co-host",
                                comedian: {
                                    id: 7,
                                    uuid: "host-uuid",
                                    name: "Host Comic",
                                    hasImage: false,
                                },
                            },
                            {
                                id: 89,
                                appearanceRole: "mention",
                                comedian: {
                                    id: 8,
                                    uuid: "mentioned-uuid",
                                    name: "Mentioned Comic",
                                    hasImage: false,
                                },
                            },
                            {
                                id: 91,
                                appearanceRole: "guest",
                                comedian: {
                                    id: 226475,
                                    uuid: "comedian-uuid",
                                    name: "Marcus D. Wiley",
                                    hasImage: true,
                                },
                            },
                        ],
                    },
                },
            ],
        } as never);

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "226475" }),
        });
        const body = await res.json();

        expect(res.status).toBe(200);
        expectOpenApiResponse("/comedians/{id}", 200, body);
        expect(body.data.podcastAppearances).toEqual([
            {
                id: 91,
                role: "guest",
                podcast: {
                    id: 6,
                    source: "podcast_index",
                    sourcePodcastId: "feed-6",
                    title: "The Green Room",
                    imageUrl: "https://cdn.example.com/podcast.jpg",
                    websiteUrl: "https://pod.example.com",
                    feedUrl: "https://pod.example.com/feed.xml",
                    authorName: "Green Room Network",
                },
                episode: {
                    id: 17,
                    source: "podcast_index",
                    sourceEpisodeId: "episode-17",
                    title: "Road Stories",
                    audioUrl: "https://cdn.example.com/episodes/17.mp3",
                    episodeUrl: "https://pod.example.com/episodes/17",
                    releaseDate: "2026-05-01T12:00:00.000Z",
                    durationSeconds: 1840,
                    hosts: [
                        {
                            id: 7,
                            uuid: "host-uuid",
                            name: "Host Comic",
                            imageUrl: "https://cdn.example.com/Host Comic.jpg",
                            hasImage: false,
                            role: "cohost",
                        },
                    ],
                    guests: [
                        {
                            id: 8,
                            uuid: "mentioned-uuid",
                            name: "Mentioned Comic",
                            imageUrl:
                                "https://cdn.example.com/Mentioned Comic.jpg",
                            hasImage: false,
                            role: "guest",
                        },
                        {
                            id: 226475,
                            uuid: "comedian-uuid",
                            name: "Marcus D. Wiley",
                            imageUrl:
                                "https://cdn.example.com/Marcus D. Wiley.jpg",
                            hasImage: true,
                            role: "guest",
                        },
                    ],
                },
            },
        ]);
    });

    it("fails the OpenAPI contract when required social data id is omitted", async () => {
        const body = {
            data: {
                id: 226475,
                uuid: "comedian-uuid",
                name: "Marcus D. Wiley",
                imageUrl: "https://cdn.example.com/Marcus D. Wiley.jpg",
                social_data: {
                    website: "https://marcusdwiley.com/",
                    popularity: 0.6,
                },
            },
        };

        expect(() => {
            expectOpenApiResponse("/comedians/{id}", 200, body);
        }).toThrow("$.data.social_data.id is required");
    });

    it("returns 500 with rate-limit headers when the detail lookup fails unexpectedly", async () => {
        mockFindUnique.mockRejectedValue(new Error("DB unavailable"));

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "226475" }),
        });
        const body = await res.json();

        expect(res.status).toBe(500);
        expect(body).toEqual({ error: "Failed to fetch comedian" });
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });
});
