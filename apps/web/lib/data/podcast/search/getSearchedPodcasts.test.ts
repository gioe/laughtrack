import { beforeEach, describe, expect, it, vi } from "vitest";

const { mockCount, mockFindMany } = vi.hoisted(() => ({
    mockCount: vi.fn(),
    mockFindMany: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        podcast: {
            count: mockCount,
            findMany: mockFindMany,
        },
    },
}));

import { getSearchedPodcasts } from "./getSearchedPodcasts";

beforeEach(() => {
    vi.clearAllMocks();
    mockCount.mockResolvedValue(0);
    mockFindMany.mockResolvedValue([]);
});

describe("getSearchedPodcasts", () => {
    it("searches title, author, and description", async () => {
        await getSearchedPodcasts({ q: "standup" });

        expect(mockCount).toHaveBeenCalledWith({
            where: {
                OR: [
                    { title: { contains: "standup", mode: "insensitive" } },
                    {
                        authorName: {
                            contains: "standup",
                            mode: "insensitive",
                        },
                    },
                    {
                        description: {
                            contains: "standup",
                            mode: "insensitive",
                        },
                    },
                ],
            },
        });
    });

    it("maps podcast rows with episode counts", async () => {
        mockCount.mockResolvedValue(1);
        mockFindMany.mockResolvedValue([
            {
                id: 12,
                slug: "good-one",
                title: "Good One",
                authorName: "Vulture",
                websiteUrl: "https://example.com",
                feedUrl: "https://example.com/feed.xml",
                imageUrl: "https://cdn.example.com/good-one.jpg",
                description: "<p>Comedy interviews</p>",
                _count: { episodes: 42 },
            },
        ]);

        const result = await getSearchedPodcasts({ q: "good" });

        expect(result).toEqual({
            total: 1,
            data: [
                {
                    id: 12,
                    slug: "good-one",
                    title: "Good One",
                    authorName: "Vulture",
                    websiteUrl: "https://example.com",
                    feedUrl: "https://example.com/feed.xml",
                    imageUrl: "https://cdn.example.com/good-one.jpg",
                    description: "Comedy interviews",
                    episodeCount: 42,
                },
            ],
        });
    });

    it("uses zero-indexed API pagination and caps page size", async () => {
        await getSearchedPodcasts({ page: "2", size: "100" });

        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                take: 50,
                skip: 100,
            }),
        );
    });
});
