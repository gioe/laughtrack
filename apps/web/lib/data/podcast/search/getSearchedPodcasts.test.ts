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
import { SortParamValue } from "@/objects/enum/sortParamValue";

beforeEach(() => {
    vi.clearAllMocks();
    mockCount.mockResolvedValue(0);
    mockFindMany.mockResolvedValue([]);
});

describe("getSearchedPodcasts", () => {
    it("only counts and returns podcasts with an accepted comedian ownership relationship", async () => {
        await getSearchedPodcasts({});

        const publicOwnershipWhere = {
            denyListEntries: {
                none: {
                    restoredAt: null,
                },
            },
            comedianPodcasts: {
                some: {
                    reviewStatus: "accepted",
                    associationType: { in: ["host", "owner"] },
                },
            },
        };

        expect(mockCount).toHaveBeenCalledWith({
            where: publicOwnershipWhere,
        });
        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: publicOwnershipWhere,
            }),
        );
    });

    it("includes podcasts without accepted comedian ownership when includeEmpty is true", async () => {
        await getSearchedPodcasts({ includeEmpty: "true" });

        expect(mockCount).toHaveBeenCalledWith({
            where: {
                denyListEntries: {
                    none: {
                        restoredAt: null,
                    },
                },
            },
        });
        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    denyListEntries: {
                        none: {
                            restoredAt: null,
                        },
                    },
                },
            }),
        );
    });

    it("searches title, author, and description", async () => {
        await getSearchedPodcasts({ q: "standup" });

        expect(mockCount).toHaveBeenCalledWith({
            where: {
                AND: [
                    {
                        denyListEntries: {
                            none: {
                                restoredAt: null,
                            },
                        },
                        comedianPodcasts: {
                            some: {
                                reviewStatus: "accepted",
                                associationType: { in: ["host", "owner"] },
                            },
                        },
                    },
                    {
                        OR: [
                            {
                                title: {
                                    contains: "standup",
                                    mode: "insensitive",
                                },
                            },
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
                    imageUrl:
                        "/api/v1/podcast-artwork?url=https%3A%2F%2Fcdn.example.com%2Fgood-one.jpg",
                    description: "Comedy interviews",
                    episodeCount: 42,
                    isFavorite: false,
                },
            ],
            filters: [],
        });
    });

    it("includes favorite rows when a profile id is provided", async () => {
        await getSearchedPodcasts({ profileId: "profile-123" });

        expect(mockFindMany).toHaveBeenCalledWith(
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

    it("uses zero-indexed API pagination and caps page size", async () => {
        await getSearchedPodcasts({ page: "2", size: "100" });

        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                take: 50,
                skip: 100,
            }),
        );
    });

    it("maps podcast sort params to stable orderBy clauses", async () => {
        await getSearchedPodcasts({ sort: SortParamValue.ActivityDesc });

        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                orderBy: [{ updatedAt: "desc" }, { id: "desc" }],
            }),
        );
    });

    it("can sort by episode count", async () => {
        await getSearchedPodcasts({ sort: SortParamValue.ShowCountDesc });

        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                orderBy: [
                    { episodes: { _count: "desc" } },
                    { title: "asc" },
                    { id: "asc" },
                ],
            }),
        );
    });
});
