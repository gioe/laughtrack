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
    it("filters to accepted local comedian-owned podcasts when a zip is resolved", async () => {
        await getTrendingPodcasts("10001");

        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    comedianPodcasts: {
                        some: expect.objectContaining({
                            reviewStatus: "accepted",
                            associationType: { in: ["host", "owner"] },
                            comedian: expect.objectContaining({
                                parentComedianId: null,
                                lineupItems: {
                                    some: {
                                        show: expect.objectContaining({
                                            date: { gt: expect.any(Date) },
                                            club: {
                                                zipCode: {
                                                    in: expect.arrayContaining([
                                                        "10001",
                                                    ]),
                                                },
                                            },
                                        }),
                                    },
                                },
                            }),
                        }),
                    },
                },
            }),
        );
    });

    it("falls back to global accepted comedian-owned podcasts when no zip is resolved", async () => {
        await getTrendingPodcasts(null);

        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    comedianPodcasts: {
                        some: {
                            reviewStatus: "accepted",
                            associationType: { in: ["host", "owner"] },
                        },
                    },
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
                imageUrl: "http://insecure.example.com/good-one.jpg",
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
                imageUrl: null,
                description: "Comedy interviews",
                episodeCount: 12,
            },
        ]);
    });
});
