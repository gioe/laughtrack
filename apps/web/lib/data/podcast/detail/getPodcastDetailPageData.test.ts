import { beforeEach, describe, expect, it, vi } from "vitest";
import { NotFoundError } from "../../../../objects/NotFoundError";

const { mockFindFirst, mockQueryRaw } = vi.hoisted(() => ({
    mockFindFirst: vi.fn(),
    mockQueryRaw: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        $queryRaw: mockQueryRaw,
        podcast: {
            findFirst: mockFindFirst,
        },
    },
}));

import {
    getPodcastDetailPageData,
    getPodcastDetailPageDataById,
} from "./getPodcastDetailPageData";

beforeEach(() => {
    vi.clearAllMocks();
    mockFindFirst.mockResolvedValue(null);
    mockQueryRaw.mockResolvedValue([]);
});

describe("getPodcastDetailPageData", () => {
    it("excludes denied comedian hosts", async () => {
        mockQueryRaw.mockResolvedValue([{ podcast_id: 5328 }]);

        await expect(
            getPodcastDetailPageData("living-the-dream"),
        ).rejects.toThrow(NotFoundError);

        expect(mockFindFirst).toHaveBeenCalledWith(
            expect.objectContaining({
                where: expect.objectContaining({
                    slug: "living-the-dream",
                    AND: [{ id: { notIn: [5328] } }],
                }),
            }),
        );
    });

    it("looks up slug detail pages only for podcasts with accepted host-role attribution", async () => {
        await expect(getPodcastDetailPageData("chrissy-chaos")).rejects.toThrow(
            NotFoundError,
        );

        expect(mockFindFirst).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    slug: "chrissy-chaos",
                    denyListEntries: {
                        none: {
                            restoredAt: null,
                        },
                    },
                    OR: [
                        {
                            comedianPodcasts: {
                                some: {
                                    reviewStatus: "accepted",
                                    associationType: "host",
                                    comedian: {
                                        visible: true,
                                        parentComedianId: null,
                                    },
                                },
                            },
                        },
                        {
                            AND: [
                                {
                                    comedianPodcasts: {
                                        none: {
                                            reviewStatus: "accepted",
                                            associationType: "host",
                                            comedian: {
                                                visible: true,
                                                parentComedianId: null,
                                            },
                                        },
                                    },
                                },
                                {
                                    comedianPodcasts: {
                                        some: {
                                            reviewStatus: "accepted",
                                            associationType: "cohost",
                                            comedian: {
                                                visible: true,
                                                parentComedianId: null,
                                            },
                                        },
                                    },
                                },
                            ],
                        },
                    ],
                },
            }),
        );
    });

    it("looks up id detail pages only for podcasts with accepted host-role attribution", async () => {
        await expect(getPodcastDetailPageDataById(42)).rejects.toThrow(
            NotFoundError,
        );

        expect(mockFindFirst).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    id: 42,
                    denyListEntries: {
                        none: {
                            restoredAt: null,
                        },
                    },
                    OR: [
                        {
                            comedianPodcasts: {
                                some: {
                                    reviewStatus: "accepted",
                                    associationType: "host",
                                    comedian: {
                                        visible: true,
                                        parentComedianId: null,
                                    },
                                },
                            },
                        },
                        {
                            AND: [
                                {
                                    comedianPodcasts: {
                                        none: {
                                            reviewStatus: "accepted",
                                            associationType: "host",
                                            comedian: {
                                                visible: true,
                                                parentComedianId: null,
                                            },
                                        },
                                    },
                                },
                                {
                                    comedianPodcasts: {
                                        some: {
                                            reviewStatus: "accepted",
                                            associationType: "cohost",
                                            comedian: {
                                                visible: true,
                                                parentComedianId: null,
                                            },
                                        },
                                    },
                                },
                            ],
                        },
                    ],
                },
            }),
        );
    });

    it("selects favorite rows when a profile id is provided", async () => {
        await expect(
            getPodcastDetailPageData("chrissy-chaos", "profile-123"),
        ).rejects.toThrow(NotFoundError);

        expect(mockFindFirst).toHaveBeenCalledWith(
            expect.objectContaining({
                select: expect.objectContaining({
                    favorites: {
                        where: { profileId: "profile-123" },
                        select: { id: true },
                    },
                }),
            }),
        );
    });

    it("maps only accepted episode appearances into episode comedian payloads", async () => {
        mockFindFirst.mockResolvedValue({
            id: 42,
            slug: "jane-show",
            title: "The Jane Show",
            authorName: "Jane Comic",
            websiteUrl: "https://pod.example",
            feedUrl: "https://pod.example/feed.xml",
            imageUrl: null,
            description: "Comedy",
            episodes: [
                {
                    id: 501,
                    title: "Comedy Cellar Stories",
                    description: "<p>A set recap.</p>",
                    releaseDate: new Date("2026-03-01T00:00:00.000Z"),
                    durationSeconds: 3_720,
                    episodeUrl: "https://pod.example/cellar",
                    audioUrl: "https://cdn.example.com/cellar.mp3",
                    appearances: [
                        {
                            comedian: {
                                id: 101,
                                uuid: "demo-comedian-101",
                                name: "Mark Normand",
                                hasImage: true,
                            },
                        },
                    ],
                },
            ],
            comedianPodcasts: [],
            _count: { episodes: 1 },
        });

        const result = await getPodcastDetailPageData("jane-show");

        expect(mockFindFirst).toHaveBeenCalledWith(
            expect.objectContaining({
                select: expect.objectContaining({
                    episodes: expect.objectContaining({
                        select: expect.objectContaining({
                            appearances: expect.objectContaining({
                                where: {
                                    reviewStatus: "accepted",
                                    comedian: { visible: true },
                                },
                            }),
                        }),
                    }),
                }),
            }),
        );
        expect(result.episodes[0].appearances).toEqual([
            {
                id: 101,
                uuid: "demo-comedian-101",
                name: "Mark Normand",
                imageUrl: "https://test.b-cdn.net/comedians/Mark%20Normand.png",
            },
        ]);
    });

    it("strips HTML tags and decodes entities in podcast and episode descriptions", async () => {
        mockFindFirst.mockResolvedValue({
            id: 42,
            slug: "jane-show",
            title: "The Jane Show",
            authorName: "Jane Comic",
            websiteUrl: "https://pod.example",
            feedUrl: "https://pod.example/feed.xml",
            imageUrl: null,
            description: "<p>Comedy interviews &amp; stories.</p>",
            episodes: [
                {
                    id: 501,
                    title: "Comedy Cellar Stories",
                    description: "<p>A set recap &amp; debrief.</p>",
                    releaseDate: new Date("2026-03-01T00:00:00.000Z"),
                    durationSeconds: 3_720,
                    episodeUrl: "https://pod.example/cellar",
                    audioUrl: "https://cdn.example.com/cellar.mp3",
                    appearances: [],
                },
            ],
            comedianPodcasts: [],
            _count: { episodes: 1 },
        });

        const result = await getPodcastDetailPageData("jane-show");

        expect(result.podcast.description).toBe("Comedy interviews & stories.");
        expect(result.episodes[0].description).toBe("A set recap & debrief.");
    });

    it("attaches hosts ahead of co-hosts on detail pages", async () => {
        mockFindFirst.mockResolvedValue({
            id: 42,
            slug: "jane-show",
            title: "The Jane Show",
            authorName: "Jane Comic",
            websiteUrl: "https://pod.example",
            feedUrl: "https://pod.example/feed.xml",
            imageUrl: null,
            description: "Comedy",
            episodes: [],
            comedianPodcasts: [
                {
                    associationType: "cohost",
                    comedian: {
                        id: 7,
                        uuid: "uuid-7",
                        name: "Co Host",
                        hasImage: false,
                        bio: null,
                        linktree: null,
                        instagramAccount: null,
                        instagramFollowers: null,
                        tiktokAccount: null,
                        tiktokFollowers: null,
                        youtubeAccount: null,
                        youtubeFollowers: null,
                        website: null,
                        popularity: 1,
                        _count: { lineupItems: 0 },
                    },
                },
                {
                    associationType: "host",
                    comedian: {
                        id: 8,
                        uuid: "uuid-8",
                        name: "Main Host",
                        hasImage: true,
                        bio: null,
                        linktree: null,
                        instagramAccount: null,
                        instagramFollowers: null,
                        tiktokAccount: null,
                        tiktokFollowers: null,
                        youtubeAccount: null,
                        youtubeFollowers: null,
                        website: null,
                        popularity: 2,
                        _count: { lineupItems: 3 },
                    },
                },
            ],
            _count: { episodes: 0 },
        });

        const result = await getPodcastDetailPageData("jane-show");

        expect(
            result.relatedComedians.map((comedian) => comedian.name),
        ).toEqual(["Main Host"]);
        expect(result.podcast.hosts).toEqual([
            {
                id: 8,
                uuid: "uuid-8",
                name: "Main Host",
                imageUrl: "https://test.b-cdn.net/comedians/Main%20Host.png",
            },
        ]);
    });

    it("attaches every co-host when no host exists on detail pages", async () => {
        mockFindFirst.mockResolvedValue({
            id: 42,
            slug: "jane-show",
            title: "The Jane Show",
            authorName: "Jane Comic",
            websiteUrl: "https://pod.example",
            feedUrl: "https://pod.example/feed.xml",
            imageUrl: null,
            description: "Comedy",
            episodes: [],
            comedianPodcasts: [
                {
                    associationType: "cohost",
                    comedian: {
                        id: 7,
                        uuid: "uuid-7",
                        name: "Co Host B",
                        hasImage: false,
                        bio: null,
                        linktree: null,
                        instagramAccount: null,
                        instagramFollowers: null,
                        tiktokAccount: null,
                        tiktokFollowers: null,
                        youtubeAccount: null,
                        youtubeFollowers: null,
                        website: null,
                        popularity: 1,
                        _count: { lineupItems: 0 },
                    },
                },
                {
                    associationType: "cohost",
                    comedian: {
                        id: 8,
                        uuid: "uuid-8",
                        name: "Co Host A",
                        hasImage: false,
                        bio: null,
                        linktree: null,
                        instagramAccount: null,
                        instagramFollowers: null,
                        tiktokAccount: null,
                        tiktokFollowers: null,
                        youtubeAccount: null,
                        youtubeFollowers: null,
                        website: null,
                        popularity: 2,
                        _count: { lineupItems: 3 },
                    },
                },
            ],
            _count: { episodes: 0 },
        });

        const result = await getPodcastDetailPageData("jane-show");

        expect(
            result.relatedComedians.map((comedian) => comedian.name),
        ).toEqual(["Co Host A", "Co Host B"]);
    });
});
