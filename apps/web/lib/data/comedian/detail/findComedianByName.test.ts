import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/db", () => ({
    db: { comedian: { findFirst: vi.fn() } },
}));
vi.mock("@/util/imageUtil", () => ({
    buildComedianImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.png`,
    ),
}));

import { findComedianByName } from "./findComedianByName";
import { db } from "@/lib/db";
import { NotFoundError } from "@/objects/NotFoundError";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { defaultComedianWebsiteHealthFields } from "@/test/comedianFixtures";

const mockFindFirst = vi.mocked(db.comedian.findFirst);

function makeHelper(
    slug: string | undefined = "alice-smith",
    profileId: string | undefined = undefined,
): QueryHelper {
    return {
        getSlug: () => slug,
        getProfileId: () => profileId,
    } as never as QueryHelper;
}

function makeComedianRow(
    overrides: Partial<{
        id: number;
        uuid: string;
        createdAt: Date;
        name: string;
        linktree: string | null;
        instagramAccount: string | null;
        instagramFollowers: number | null;
        tiktokAccount: string | null;
        tiktokFollowers: number | null;
        youtubeAccount: string | null;
        youtubeFollowers: number | null;
        website: string | null;
        popularity: number;
        totalShows: number;
        soldOutShows: number;
        hasImage: boolean;
        visible: boolean;
        homeCity: string | null;
        homeState: string | null;
        homeCountry: string | null;
        homeClubId: number | null;
        homeClub: { id: number; name: string } | null;
        homeLocationUpdatedAt: Date | null;
        parentComedianId: number | null;
        songkickId: string | null;
        bandsintownId: string | null;
        websiteDiscoverySource: string | null;
        websiteLastScraped: Date | null;
        websiteScrapeStrategy: string | null;
        websiteScrapingUrl: string | null;
        websiteConfidence: string | null;
        websiteScrapingUrlConfidence: string | null;
        websiteHealthStatus: string | null;
        websiteHealthFailureCount: number;
        websiteHealthCheckedAt: Date | null;
        websiteScrapingUrlHealthStatus: string | null;
        websiteScrapingUrlHealthFailureCount: number;
        websiteScrapingUrlHealthCheckedAt: Date | null;
        lineupItems: {
            id: number;
            show: {
                id: number;
                date: Date;
                name: string | null;
                club: {
                    id: number;
                    name: string;
                    city: string | null;
                    state: string | null;
                };
            };
        }[];
        podcastAppearances: {
            id: number;
            podcastName: string;
            podcastImageUrl: string | null;
            podcastAuthorName: string | null;
            podcastWebsiteUrl: string | null;
            episodeTitle: string;
            releaseDate: Date | null;
            episodeUrl: string;
        }[];
        episodeAppearances: {
            id: number;
            appearanceRole: string;
            episode: {
                id: number;
                title: string;
                releaseDate: Date | null;
                episodeUrl: string | null;
                audioUrl: string | null;
                durationSeconds: number | null;
                podcast: {
                    id: number;
                    title: string;
                    imageUrl: string | null;
                    authorName: string | null;
                    websiteUrl: string | null;
                };
            };
        }[];
        favoriteComedians: { id: number }[];
    }> = {},
) {
    return {
        id: 1,
        uuid: "uuid-1",
        createdAt: new Date("2026-05-01T12:00:00.000Z"),
        name: "Alice Smith",
        linktree: null,
        instagramAccount: "@alice",
        instagramFollowers: 5000,
        tiktokAccount: null,
        tiktokFollowers: null,
        youtubeAccount: null,
        youtubeFollowers: null,
        website: "https://alice.example.com",
        popularity: 80,
        hasImage: true,
        visible: true,
        homeCity: null,
        homeState: null,
        homeCountry: null,
        homeClubId: null,
        homeClub: null,
        homeLocationUpdatedAt: null,
        totalShows: 0,
        soldOutShows: 0,
        parentComedianId: null,
        songkickId: null,
        bandsintownId: null,
        websiteDiscoverySource: null,
        websiteLastScraped: null,
        websiteScrapeStrategy: null,
        websiteScrapingUrl: null,
        websiteConfidence: null,
        websiteScrapingUrlConfidence: null,
        tourSourceReviewEvidence: null,
        ...defaultComedianWebsiteHealthFields,
        lineupItems: [
            {
                id: 10,
                show: {
                    id: 101,
                    date: new Date("2026-05-01T20:00:00.000Z"),
                    name: "Friday Night",
                    club: {
                        id: 201,
                        name: "Comedy Club",
                        city: "Austin",
                        state: "TX",
                    },
                },
            },
            {
                id: 11,
                show: {
                    id: 102,
                    date: new Date("2026-05-02T20:00:00.000Z"),
                    name: null,
                    club: {
                        id: 202,
                        name: "Laugh Room",
                        city: "Dallas",
                        state: "TX",
                    },
                },
            },
            {
                id: 12,
                show: {
                    id: 103,
                    date: new Date("2026-05-03T20:00:00.000Z"),
                    name: "Late Show",
                    club: {
                        id: 201,
                        name: "Comedy Club",
                        city: "Austin",
                        state: "TX",
                    },
                },
            },
        ],
        podcastAppearances: [],
        episodeAppearances: [],
        favoriteComedians: [],
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("findComedianByName", () => {
    describe("showCount", () => {
        it("equals lineupItems.length from the mocked Prisma response", async () => {
            const row = makeComedianRow({
                lineupItems: [
                    ...makeComedianRow().lineupItems,
                    {
                        id: 4,
                        show: {
                            id: 104,
                            date: new Date("2026-05-04T20:00:00.000Z"),
                            name: "Fourth Show",
                            club: {
                                id: 204,
                                name: "Fourth Club",
                                city: "Houston",
                                state: "TX",
                            },
                        },
                    },
                    {
                        id: 5,
                        show: {
                            id: 105,
                            date: new Date("2026-05-05T20:00:00.000Z"),
                            name: "Fifth Show",
                            club: {
                                id: 205,
                                name: "Fifth Club",
                                city: "San Antonio",
                                state: "TX",
                            },
                        },
                    },
                ],
            });
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(makeHelper());

            expect(result.showCount).toBe(5);
        });

        it("is 0 when lineupItems is empty", async () => {
            const row = makeComedianRow({ lineupItems: [] });
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(makeHelper());

            expect(result.showCount).toBe(0);
        });
    });

    describe("homeLocation", () => {
        it("maps derived home city and linked home club onto the DTO", async () => {
            const row = makeComedianRow({
                homeCity: "Austin",
                homeState: "TX",
                homeCountry: "USA",
                homeClubId: 201,
                homeClub: { id: 201, name: "Comedy Club" },
            });
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(makeHelper());

            expect(result.homeLocation).toEqual({
                city: "Austin",
                state: "TX",
                country: "USA",
                club: { id: 201, name: "Comedy Club" },
            });
        });

        it("falls back to a null club and null fields when home location is unset", async () => {
            const row = makeComedianRow();
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(makeHelper());

            expect(result.homeLocation).toEqual({
                city: null,
                state: null,
                country: null,
                club: null,
            });
        });
    });

    describe("dates", () => {
        it("maps upcoming show city data into dates for header city counts", async () => {
            const row = makeComedianRow();
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(makeHelper());

            expect(result.dates).toEqual([
                {
                    id: 101,
                    date: new Date("2026-05-01T20:00:00.000Z"),
                    name: "Friday Night",
                    clubId: 201,
                    clubName: "Comedy Club",
                    clubCity: "Austin",
                    clubState: "TX",
                    imageUrl: "https://cdn.example.com/Alice Smith.png",
                },
                {
                    id: 102,
                    date: new Date("2026-05-02T20:00:00.000Z"),
                    name: null,
                    clubId: 202,
                    clubName: "Laugh Room",
                    clubCity: "Dallas",
                    clubState: "TX",
                    imageUrl: "https://cdn.example.com/Alice Smith.png",
                },
                {
                    id: 103,
                    date: new Date("2026-05-03T20:00:00.000Z"),
                    name: "Late Show",
                    clubId: 201,
                    clubName: "Comedy Club",
                    clubCity: "Austin",
                    clubState: "TX",
                    imageUrl: "https://cdn.example.com/Alice Smith.png",
                },
            ]);
        });
    });

    describe("isFavorite", () => {
        it("is true when favoriteComedians array is non-empty", async () => {
            const row = makeComedianRow({ favoriteComedians: [{ id: 99 }] });
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(
                makeHelper("alice-smith", "profile-1"),
            );

            expect(result.isFavorite).toBe(true);
        });

        it("is false when favoriteComedians array is empty", async () => {
            const row = makeComedianRow({ favoriteComedians: [] });
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(
                makeHelper("alice-smith", "profile-1"),
            );

            expect(result.isFavorite).toBe(false);
        });

        it("is false when favoriteComedians is absent (no profileId)", async () => {
            const row = makeComedianRow();
            delete (row as Record<string, unknown>).favoriteComedians;
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(makeHelper());

            expect(result.isFavorite).toBe(false);
        });
    });

    describe("hasImage propagation", () => {
        it("sets hasImage=true when DB row has hasImage=true", async () => {
            const row = makeComedianRow({ hasImage: true });
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(makeHelper());

            expect(result.hasImage).toBe(true);
        });

        it("sets hasImage=false when DB row has hasImage=false", async () => {
            const row = makeComedianRow({ hasImage: false });
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(makeHelper());

            expect(result.hasImage).toBe(false);
        });
    });

    describe("podcastAppearances", () => {
        it("maps accepted episode appearance fields most-recent first", async () => {
            const row = makeComedianRow({
                episodeAppearances: [
                    {
                        id: 1,
                        appearanceRole: "guest",
                        episode: {
                            id: 1001,
                            podcast: {
                                id: 501,
                                title: "Older Pod",
                                imageUrl: "https://cdn.example.com/older.jpg",
                                authorName: "Older Network",
                                websiteUrl: "https://older.example.com",
                            },
                            title: "Older Episode",
                            releaseDate: new Date("2024-01-01T00:00:00.000Z"),
                            episodeUrl: "https://example.com/older",
                            audioUrl: "https://cdn.example.com/older.mp3",
                            durationSeconds: 3600,
                        },
                    },
                    {
                        id: 2,
                        appearanceRole: "host",
                        episode: {
                            id: 1002,
                            podcast: {
                                id: 502,
                                title: "Newer Pod",
                                imageUrl: "https://cdn.example.com/newer.jpg",
                                authorName: "Newer Network",
                                websiteUrl: "https://newer.example.com",
                            },
                            title: "Newer Episode",
                            releaseDate: new Date("2025-01-01T00:00:00.000Z"),
                            episodeUrl: "https://example.com/newer",
                            audioUrl: "https://cdn.example.com/newer.mp3",
                            durationSeconds: 4200,
                        },
                    },
                    {
                        id: 3,
                        appearanceRole: "guest",
                        episode: {
                            id: 1003,
                            podcast: {
                                id: 503,
                                title: "Undated Pod",
                                imageUrl: null,
                                authorName: null,
                                websiteUrl: null,
                            },
                            title: "Undated Episode",
                            releaseDate: null,
                            episodeUrl: "https://example.com/undated",
                            audioUrl: "https://cdn.example.com/undated.mp3",
                            durationSeconds: null,
                        },
                    },
                ],
            });
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(makeHelper());

            expect(result.podcastAppearances).toEqual([
                {
                    id: 2,
                    podcastName: "Newer Pod",
                    podcastImageUrl: "https://cdn.example.com/newer.jpg",
                    podcastAuthorName: "Newer Network",
                    podcastWebsiteUrl: "https://newer.example.com",
                    episodeTitle: "Newer Episode",
                    releaseDate: new Date("2025-01-01T00:00:00.000Z"),
                    episodeUrl: "https://example.com/newer",
                    audioUrl: "https://cdn.example.com/newer.mp3",
                    durationSeconds: 4200,
                    appearanceRole: "host",
                },
                {
                    id: 1,
                    podcastName: "Older Pod",
                    podcastImageUrl: "https://cdn.example.com/older.jpg",
                    podcastAuthorName: "Older Network",
                    podcastWebsiteUrl: "https://older.example.com",
                    episodeTitle: "Older Episode",
                    releaseDate: new Date("2024-01-01T00:00:00.000Z"),
                    episodeUrl: "https://example.com/older",
                    audioUrl: "https://cdn.example.com/older.mp3",
                    durationSeconds: 3600,
                    appearanceRole: "guest",
                },
                {
                    id: 3,
                    podcastName: "Undated Pod",
                    podcastImageUrl: null,
                    podcastAuthorName: null,
                    podcastWebsiteUrl: null,
                    episodeTitle: "Undated Episode",
                    releaseDate: null,
                    episodeUrl: "https://example.com/undated",
                    audioUrl: "https://cdn.example.com/undated.mp3",
                    durationSeconds: null,
                    appearanceRole: "guest",
                },
            ]);
        });

        it("requests only accepted episode appearances with playable audio from Prisma", async () => {
            const row = makeComedianRow();
            mockFindFirst.mockResolvedValue(row);

            await findComedianByName(makeHelper());

            expect(mockFindFirst).toHaveBeenCalledWith(
                expect.objectContaining({
                    select: expect.objectContaining({
                        episodeAppearances: expect.objectContaining({
                            select: expect.objectContaining({
                                appearanceRole: true,
                                episode: expect.objectContaining({
                                    select: expect.objectContaining({
                                        audioUrl: true,
                                        durationSeconds: true,
                                        podcast: expect.objectContaining({
                                            select: expect.objectContaining({
                                                imageUrl: true,
                                                authorName: true,
                                                websiteUrl: true,
                                            }),
                                        }),
                                    }),
                                }),
                            }),
                            where: {
                                reviewStatus: "accepted",
                                AND: [
                                    {
                                        episode: {
                                            audioUrl: {
                                                not: null,
                                            },
                                        },
                                    },
                                    {
                                        episode: {
                                            audioUrl: {
                                                not: "",
                                            },
                                        },
                                    },
                                ],
                            },
                            orderBy: [
                                { episode: { releaseDate: "desc" } },
                                { id: "desc" },
                            ],
                        }),
                    }),
                }),
            );
        });
    });

    describe("podcastAppearances dedupe", () => {
        // Scraper writes the same logical podcast episode to multiple
        // `podcast_episodes` rows (different feeds, prefix variants), each
        // joined by its own episode_appearance. The data layer collapses these
        // by (podcast.id, episode.releaseDate.getTime()) so the iOS Podcasts tab
        // sees one row per logical episode.

        it("collapses duplicate episodes that share the same podcast and release timestamp", async () => {
            const releaseDate = new Date("2026-05-12T01:00:00.000Z");
            const row = makeComedianRow({
                episodeAppearances: [
                    // Tuesdays with Stories! "#655 Fart In My Mouth..." — two
                    // podcast_episodes rows for the exact same logical episode.
                    {
                        id: 715587,
                        appearanceRole: "host",
                        episode: {
                            id: 392861,
                            podcast: {
                                id: 5660,
                                title: "Tuesdays with Stories!",
                                imageUrl: null,
                                authorName: null,
                                websiteUrl: null,
                            },
                            title: "#655 Fart In My Mouth and Call It a Love Story",
                            releaseDate,
                            episodeUrl: "https://example.com/655-a",
                            audioUrl: "https://cdn.example.com/655-a.mp3",
                            durationSeconds: 3600,
                        },
                    },
                    {
                        id: 92841,
                        appearanceRole: "host",
                        episode: {
                            id: 58823,
                            podcast: {
                                id: 5660,
                                title: "Tuesdays with Stories!",
                                imageUrl: null,
                                authorName: null,
                                websiteUrl: null,
                            },
                            title: "#655 Fart In My Mouth and Call It a Love Story",
                            releaseDate,
                            episodeUrl: "https://example.com/655-b",
                            audioUrl: "https://cdn.example.com/655-b.mp3",
                            durationSeconds: 3600,
                        },
                    },
                ],
            });
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(makeHelper());

            expect(result.podcastAppearances).toHaveLength(1);
            // The higher appearance.id wins the tiebreak (most recent scrape).
            expect(result.podcastAppearances?.[0]?.id).toBe(715587);
        });

        it("collapses prefix-variant duplicates that share the same podcast and release timestamp", async () => {
            // "67: Wife Got Fat..." and "Wife Got Fat..." — different prefix,
            // same logical episode. Same podcast + identical releaseDate
            // timestamp collapses them.
            const releaseDate = new Date("2026-04-07T13:28:00.000Z");
            const row = makeComedianRow({
                episodeAppearances: [
                    {
                        id: 1,
                        appearanceRole: "guest",
                        episode: {
                            id: 49592,
                            podcast: {
                                id: 700,
                                title: "Jim Norton Can't Save You",
                                imageUrl: null,
                                authorName: null,
                                websiteUrl: null,
                            },
                            title: "Wife Got Fat with Mark Normand & Shaun Murphy | Jim Norton Can't Save You EP 65",
                            releaseDate,
                            episodeUrl: "https://example.com/no-prefix",
                            audioUrl: "https://cdn.example.com/no-prefix.mp3",
                            durationSeconds: 4000,
                        },
                    },
                    {
                        id: 2,
                        appearanceRole: "guest",
                        episode: {
                            id: 183845,
                            podcast: {
                                id: 700,
                                title: "Jim Norton Can't Save You",
                                imageUrl: null,
                                authorName: null,
                                websiteUrl: null,
                            },
                            title: "67: Wife Got Fat with Mark Normand & Shaun Murphy | Jim Norton Can't Save You EP 65",
                            releaseDate,
                            episodeUrl: "https://example.com/prefix",
                            audioUrl: "https://cdn.example.com/prefix.mp3",
                            durationSeconds: 4000,
                        },
                    },
                ],
            });
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(makeHelper());

            expect(result.podcastAppearances).toHaveLength(1);
        });

        it("prefers the host role over guest when collapsing duplicates", async () => {
            const releaseDate = new Date("2026-03-01T00:00:00.000Z");
            const row = makeComedianRow({
                episodeAppearances: [
                    {
                        id: 10,
                        appearanceRole: "guest",
                        episode: {
                            id: 200,
                            podcast: {
                                id: 800,
                                title: "Mixed Roles Pod",
                                imageUrl: null,
                                authorName: null,
                                websiteUrl: null,
                            },
                            title: "Episode 1",
                            releaseDate,
                            episodeUrl: "https://example.com/guest",
                            audioUrl: "https://cdn.example.com/guest.mp3",
                            durationSeconds: 3000,
                        },
                    },
                    {
                        id: 11,
                        appearanceRole: "host",
                        episode: {
                            id: 201,
                            podcast: {
                                id: 800,
                                title: "Mixed Roles Pod",
                                imageUrl: null,
                                authorName: null,
                                websiteUrl: null,
                            },
                            title: "Episode 1",
                            releaseDate,
                            episodeUrl: "https://example.com/host",
                            audioUrl: "https://cdn.example.com/host.mp3",
                            durationSeconds: 3000,
                        },
                    },
                ],
            });
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(makeHelper());

            expect(result.podcastAppearances).toHaveLength(1);
            expect(result.podcastAppearances?.[0]?.appearanceRole).toBe("host");
        });

        it("picks the host role even when the host appearance has the lower id (role priority dominates the id tiebreaker)", async () => {
            // Mirror of the test above with appearance.id ordering inverted.
            // If role priority were absent, the id tiebreaker alone would keep
            // the guest (higher id wins). The host must still win.
            const releaseDate = new Date("2026-03-02T00:00:00.000Z");
            const row = makeComedianRow({
                episodeAppearances: [
                    {
                        id: 50,
                        appearanceRole: "host",
                        episode: {
                            id: 210,
                            podcast: {
                                id: 810,
                                title: "Inverted IDs Pod",
                                imageUrl: null,
                                authorName: null,
                                websiteUrl: null,
                            },
                            title: "Episode A",
                            releaseDate,
                            episodeUrl: "https://example.com/host-low-id",
                            audioUrl: "https://cdn.example.com/host-low-id.mp3",
                            durationSeconds: 3000,
                        },
                    },
                    {
                        id: 99,
                        appearanceRole: "guest",
                        episode: {
                            id: 211,
                            podcast: {
                                id: 810,
                                title: "Inverted IDs Pod",
                                imageUrl: null,
                                authorName: null,
                                websiteUrl: null,
                            },
                            title: "Episode A",
                            releaseDate,
                            episodeUrl: "https://example.com/guest-high-id",
                            audioUrl: "https://cdn.example.com/guest-high-id.mp3",
                            durationSeconds: 3000,
                        },
                    },
                ],
            });
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(makeHelper());

            expect(result.podcastAppearances).toHaveLength(1);
            expect(result.podcastAppearances?.[0]?.appearanceRole).toBe("host");
        });

        it("picks the cohost role over guest when collapsing duplicates", async () => {
            const releaseDate = new Date("2026-03-03T00:00:00.000Z");
            const row = makeComedianRow({
                episodeAppearances: [
                    {
                        id: 60,
                        appearanceRole: "guest",
                        episode: {
                            id: 220,
                            podcast: {
                                id: 820,
                                title: "Cohost Pod",
                                imageUrl: null,
                                authorName: null,
                                websiteUrl: null,
                            },
                            title: "Episode B",
                            releaseDate,
                            episodeUrl: "https://example.com/guest",
                            audioUrl: "https://cdn.example.com/guest.mp3",
                            durationSeconds: 2700,
                        },
                    },
                    {
                        id: 61,
                        appearanceRole: "cohost",
                        episode: {
                            id: 221,
                            podcast: {
                                id: 820,
                                title: "Cohost Pod",
                                imageUrl: null,
                                authorName: null,
                                websiteUrl: null,
                            },
                            title: "Episode B",
                            releaseDate,
                            episodeUrl: "https://example.com/cohost",
                            audioUrl: "https://cdn.example.com/cohost.mp3",
                            durationSeconds: 2700,
                        },
                    },
                ],
            });
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(makeHelper());

            expect(result.podcastAppearances).toHaveLength(1);
            expect(result.podcastAppearances?.[0]?.appearanceRole).toBe(
                "cohost",
            );
        });

        it("keeps different podcasts that happen to publish on the same timestamp", async () => {
            // Two distinct podcasts releasing at the same moment are NOT
            // duplicates — the dedup key includes podcast.id.
            const releaseDate = new Date("2026-02-14T12:00:00.000Z");
            const row = makeComedianRow({
                episodeAppearances: [
                    {
                        id: 20,
                        appearanceRole: "guest",
                        episode: {
                            id: 300,
                            podcast: {
                                id: 900,
                                title: "Pod A",
                                imageUrl: null,
                                authorName: null,
                                websiteUrl: null,
                            },
                            title: "Shared Day Episode",
                            releaseDate,
                            episodeUrl: "https://example.com/a",
                            audioUrl: "https://cdn.example.com/a.mp3",
                            durationSeconds: 1800,
                        },
                    },
                    {
                        id: 21,
                        appearanceRole: "guest",
                        episode: {
                            id: 301,
                            podcast: {
                                id: 901,
                                title: "Pod B",
                                imageUrl: null,
                                authorName: null,
                                websiteUrl: null,
                            },
                            title: "Shared Day Episode",
                            releaseDate,
                            episodeUrl: "https://example.com/b",
                            audioUrl: "https://cdn.example.com/b.mp3",
                            durationSeconds: 1800,
                        },
                    },
                ],
            });
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(makeHelper());

            expect(result.podcastAppearances).toHaveLength(2);
        });

        it("falls back to (podcastId, title) when releaseDate is null on both copies", async () => {
            const row = makeComedianRow({
                episodeAppearances: [
                    {
                        id: 30,
                        appearanceRole: "guest",
                        episode: {
                            id: 400,
                            podcast: {
                                id: 1000,
                                title: "Undated Pod",
                                imageUrl: null,
                                authorName: null,
                                websiteUrl: null,
                            },
                            title: "Same Title",
                            releaseDate: null,
                            episodeUrl: "https://example.com/u1",
                            audioUrl: "https://cdn.example.com/u1.mp3",
                            durationSeconds: 2400,
                        },
                    },
                    {
                        id: 31,
                        appearanceRole: "guest",
                        episode: {
                            id: 401,
                            podcast: {
                                id: 1000,
                                title: "Undated Pod",
                                imageUrl: null,
                                authorName: null,
                                websiteUrl: null,
                            },
                            title: "Same Title",
                            releaseDate: null,
                            episodeUrl: "https://example.com/u2",
                            audioUrl: "https://cdn.example.com/u2.mp3",
                            durationSeconds: 2400,
                        },
                    },
                ],
            });
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(makeHelper());

            expect(result.podcastAppearances).toHaveLength(1);
        });
    });

    describe("NotFoundError", () => {
        it("throws NotFoundError when db.comedian.findFirst returns null", async () => {
            mockFindFirst.mockResolvedValue(null);

            await expect(findComedianByName(makeHelper())).rejects.toThrow(
                NotFoundError,
            );
        });

        it("includes the comedian name in the error message", async () => {
            mockFindFirst.mockResolvedValue(null);

            await expect(
                findComedianByName(makeHelper("bob-jones")),
            ).rejects.toThrow("bob-jones");
        });
    });
});
