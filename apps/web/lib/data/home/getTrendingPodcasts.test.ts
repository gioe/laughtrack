import { beforeEach, describe, expect, it, vi } from "vitest";

const { mockFindMany } = vi.hoisted(() => ({
    mockFindMany: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        podcast: {
            findMany: mockFindMany,
        },
    },
}));

import { getTrendingPodcasts } from "./getTrendingPodcasts";

beforeEach(() => {
    vi.clearAllMocks();
    mockFindMany.mockResolvedValue([]);
});

describe("getTrendingPodcasts", () => {
    it("filters to accepted local host-attributed podcasts when a zip is resolved", async () => {
        await getTrendingPodcasts("10001");

        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    denyListEntries: {
                        none: {
                            restoredAt: null,
                        },
                    },
                    OR: [
                        {
                            comedianPodcasts: {
                                some: expect.objectContaining({
                                    reviewStatus: "accepted",
                                    associationType: "host",
                                    comedian: expect.objectContaining({
                                        parentComedianId: null,
                                        lineupItems: {
                                            some: {
                                                show: expect.objectContaining({
                                                    date: {
                                                        gt: expect.any(Date),
                                                    },
                                                    club: {
                                                        zipCode: {
                                                            in: expect.arrayContaining(
                                                                ["10001"],
                                                            ),
                                                        },
                                                    },
                                                }),
                                            },
                                        },
                                    }),
                                }),
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
                                        some: expect.objectContaining({
                                            reviewStatus: "accepted",
                                            associationType: "cohost",
                                            comedian: expect.objectContaining({
                                                parentComedianId: null,
                                                lineupItems: {
                                                    some: {
                                                        show: expect.objectContaining(
                                                            {
                                                                date: {
                                                                    gt: expect.any(
                                                                        Date,
                                                                    ),
                                                                },
                                                                club: {
                                                                    zipCode: {
                                                                        in: expect.arrayContaining(
                                                                            [
                                                                                "10001",
                                                                            ],
                                                                        ),
                                                                    },
                                                                },
                                                            },
                                                        ),
                                                    },
                                                },
                                            }),
                                        }),
                                    },
                                },
                            ],
                        },
                    ],
                },
            }),
        );
    });

    it("falls back to global accepted host-attributed podcasts when no zip is resolved", async () => {
        await getTrendingPodcasts(null);

        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
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

    it("ranks by favorite count with stable episode/title/id tiebreakers", async () => {
        await getTrendingPodcasts(null);

        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                orderBy: [
                    { favorites: { _count: "desc" } },
                    { episodes: { _count: "desc" } },
                    { title: "asc" },
                    { id: "asc" },
                ],
            }),
        );
    });

    it("maps database rows to the home-feed podcast shape", async () => {
        mockFindMany.mockResolvedValue([
            {
                id: 42,
                slug: "good-one",
                title: "Good One",
                authorName: "Vulture",
                websiteUrl: "https://example.com/good-one",
                feedUrl: "https://example.com/feed.xml",
                imageUrl: "http://cdn.example.com/good-one.jpg",
                description: "<p>Comedy interviews</p>",
                _count: { episodes: 12 },
            },
        ]);

        await expect(getTrendingPodcasts(null)).resolves.toEqual([
            {
                id: 42,
                slug: "good-one",
                title: "Good One",
                authorName: "Vulture",
                websiteUrl: "https://example.com/good-one",
                feedUrl: "https://example.com/feed.xml",
                imageUrl:
                    "/api/v1/podcast-artwork?url=https%3A%2F%2Fcdn.example.com%2Fgood-one.jpg",
                description: "Comedy interviews",
                episodeCount: 12,
            },
        ]);
    });
});
