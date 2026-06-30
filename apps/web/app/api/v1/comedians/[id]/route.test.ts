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
            visible: true,
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
        expect(body.data.socialData).toMatchObject({
            id: 226475,
            website: "https://marcusdwiley.com/",
            popularity: 0.6,
        });
    });

    it("maps derived home location (city + home club) into the detail response", async () => {
        mockFindUnique.mockResolvedValue({
            id: 226475,
            uuid: "comedian-uuid",
            name: "Marcus D. Wiley",
            visible: true,
            linktree: null,
            instagramAccount: null,
            instagramFollowers: null,
            tiktokAccount: null,
            tiktokFollowers: null,
            youtubeAccount: null,
            youtubeFollowers: null,
            website: null,
            popularity: 0.6,
            hasImage: false,
            homeCity: "Houston",
            homeState: "TX",
            homeCountry: "USA",
            homeClub: { id: 42, name: "The Secret Group" },
            episodeAppearances: [],
        } as never);

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "226475" }),
        });
        const body = await res.json();

        expect(res.status).toBe(200);
        expectOpenApiResponse("/comedians/{id}", 200, body);
        expect(body.data.homeLocation).toEqual({
            city: "Houston",
            state: "TX",
            country: "USA",
            clubId: 42,
            clubName: "The Secret Group",
        });
    });

    it("nulls home location fields and club when the comedian has no derived home", async () => {
        mockFindUnique.mockResolvedValue({
            id: 226475,
            uuid: "comedian-uuid",
            name: "Marcus D. Wiley",
            visible: true,
            linktree: null,
            instagramAccount: null,
            instagramFollowers: null,
            tiktokAccount: null,
            tiktokFollowers: null,
            youtubeAccount: null,
            youtubeFollowers: null,
            website: null,
            popularity: 0.6,
            hasImage: false,
            homeCity: null,
            homeState: null,
            homeCountry: null,
            homeClub: null,
            episodeAppearances: [],
        } as never);

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "226475" }),
        });
        const body = await res.json();

        expect(res.status).toBe(200);
        expectOpenApiResponse("/comedians/{id}", 200, body);
        expect(body.data.homeLocation).toEqual({
            city: null,
            state: null,
            country: null,
            clubId: null,
            clubName: null,
        });
    });

    it("returns podcast appearance episode DTOs for the iOS OpenAPI contract", async () => {
        mockFindUnique.mockResolvedValue({
            id: 226475,
            uuid: "comedian-uuid",
            name: "Marcus D. Wiley",
            visible: true,
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

    it("collapses duplicate podcast appearances that share the same (podcastId, releaseDate)", async () => {
        // Repro of the iOS Podcasts-tab bug: same logical episode lives in
        // podcast_episodes as multiple rows (different feeds or prefix
        // variants), each generating its own episode_appearance for the same
        // comedian. The v1 route must dedupe before returning to iOS.
        const releaseDate = new Date("2026-05-12T01:00:00.000Z");
        mockFindUnique.mockResolvedValue({
            id: 874,
            uuid: "mark-normand-uuid",
            name: "Mark Normand",
            visible: true,
            totalShows: 0,
            soldOutShows: 0,
            linktree: null,
            instagramAccount: null,
            instagramFollowers: null,
            tiktokAccount: null,
            tiktokFollowers: null,
            youtubeAccount: null,
            youtubeFollowers: null,
            website: null,
            popularity: 0.9,
            hasImage: true,
            ...defaultComedianWebsiteHealthFields,
            episodeAppearances: [
                {
                    id: 715587,
                    appearanceRole: "host",
                    episode: {
                        id: 392861,
                        source: "podcast_index",
                        sourceEpisodeId: "tws-655-a",
                        title: "#655 Fart In My Mouth and Call It a Love Story",
                        releaseDate,
                        durationSeconds: 3600,
                        episodeUrl: "https://example.com/655-a",
                        audioUrl: "https://cdn.example.com/655-a.mp3",
                        podcast: {
                            id: 5660,
                            source: "podcast_index",
                            sourcePodcastId: "tws-feed",
                            title: "Tuesdays with Stories!",
                            imageUrl: null,
                            websiteUrl: null,
                            feedUrl: null,
                            authorName: null,
                        },
                        appearances: [],
                    },
                },
                {
                    id: 92841,
                    appearanceRole: "host",
                    episode: {
                        id: 58823,
                        source: "podcast_index",
                        sourceEpisodeId: "tws-655-b",
                        title: "#655 Fart In My Mouth and Call It a Love Story",
                        releaseDate,
                        durationSeconds: 3600,
                        episodeUrl: "https://example.com/655-b",
                        audioUrl: "https://cdn.example.com/655-b.mp3",
                        podcast: {
                            id: 5660,
                            source: "podcast_index",
                            sourcePodcastId: "tws-feed",
                            title: "Tuesdays with Stories!",
                            imageUrl: null,
                            websiteUrl: null,
                            feedUrl: null,
                            authorName: null,
                        },
                        appearances: [],
                    },
                },
            ],
        } as never);

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "874" }),
        });
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.data.podcastAppearances).toHaveLength(1);
        // Higher appearance.id wins the same-role tiebreaker (most recent scrape).
        expect(body.data.podcastAppearances[0].id).toBe(715587);
    });

    it("fails the OpenAPI contract when required social data id is omitted", async () => {
        const body = {
            data: {
                id: 226475,
                uuid: "comedian-uuid",
                name: "Marcus D. Wiley",
                imageUrl: "https://cdn.example.com/Marcus D. Wiley.jpg",
                socialData: {
                    website: "https://marcusdwiley.com/",
                    popularity: 0.6,
                },
            },
        };

        expect(() => {
            expectOpenApiResponse("/comedians/{id}", 200, body);
        }).toThrow("$.data.socialData.id is required");
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

    it("returns 404 when the requested comedian is hidden (visible=false)", async () => {
        mockFindUnique.mockResolvedValue({
            id: 226475,
            uuid: "comedian-uuid",
            name: "Hidden Comic",
            visible: false,
            episodeAppearances: [],
        } as never);

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "226475" }),
        });
        const body = await res.json();

        expect(res.status).toBe(404);
        expect(body).toEqual({ error: "Comedian not found" });
    });
});
