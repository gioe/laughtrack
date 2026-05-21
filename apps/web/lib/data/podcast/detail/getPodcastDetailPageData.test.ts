import { beforeEach, describe, expect, it, vi } from "vitest";
import { NotFoundError } from "../../../../objects/NotFoundError";

const { mockFindFirst } = vi.hoisted(() => ({
    mockFindFirst: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
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
});

describe("getPodcastDetailPageData", () => {
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
                                        },
                                    },
                                },
                                {
                                    comedianPodcasts: {
                                        some: {
                                            reviewStatus: "accepted",
                                            associationType: "cohost",
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
                                        },
                                    },
                                },
                                {
                                    comedianPodcasts: {
                                        some: {
                                            reviewStatus: "accepted",
                                            associationType: "cohost",
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

        expect(result.relatedComedians.map((comedian) => comedian.name)).toEqual(
            ["Main Host"],
        );
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

        expect(result.relatedComedians.map((comedian) => comedian.name)).toEqual(
            ["Co Host A", "Co Host B"],
        );
    });
});
