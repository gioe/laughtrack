import { beforeEach, describe, expect, it, vi } from "vitest";

const { mockCount, mockFindMany, mockQueryRaw } = vi.hoisted(() => ({
    mockCount: vi.fn(),
    mockFindMany: vi.fn(),
    mockQueryRaw: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        $queryRaw: mockQueryRaw,
        podcast: {
            count: mockCount,
            findMany: mockFindMany,
        },
    },
}));

import { getSearchedPodcasts } from "./getSearchedPodcasts";
import { SortParamValue } from "@/objects/enum/sortParamValue";

const canonicalComedianWhere = {
    visible: true,
    parentComedianId: null,
};

const publicAttributionWhere = {
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
                    comedian: canonicalComedianWhere,
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
                            comedian: canonicalComedianWhere,
                        },
                    },
                },
                {
                    comedianPodcasts: {
                        some: {
                            reviewStatus: "accepted",
                            associationType: "cohost",
                            comedian: canonicalComedianWhere,
                        },
                    },
                },
            ],
        },
    ],
};

beforeEach(() => {
    vi.clearAllMocks();
    mockCount.mockResolvedValue(0);
    mockFindMany.mockResolvedValue([]);
    mockQueryRaw.mockResolvedValue([]);
});

describe("getSearchedPodcasts", () => {
    it("excludes denied comedian hosts", async () => {
        mockQueryRaw.mockResolvedValue([{ podcast_id: 5328 }]);

        await getSearchedPodcasts({});

        expect(mockCount).toHaveBeenCalledWith({
            where: {
                ...publicAttributionWhere,
                AND: [{ id: { notIn: [5328] } }],
            },
        });
        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    ...publicAttributionWhere,
                    AND: [{ id: { notIn: [5328] } }],
                },
            }),
        );

        const sql = mockQueryRaw.mock.calls[0][0] as {
            strings: readonly string[];
        };
        const sqlText = sql.strings.join(" ");
        expect(sqlText).toContain("comedian_deny_list");
        expect(sqlText).toContain("cp.review_status = 'accepted'");
        expect(sqlText).toContain("cp.association_type IN ('host', 'cohost')");
        expect(sqlText).toContain("regexp_replace");
    });

    it("only counts and returns podcasts with accepted host-role attribution", async () => {
        await getSearchedPodcasts({});

        expect(mockCount).toHaveBeenCalledWith({
            where: publicAttributionWhere,
        });
        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: publicAttributionWhere,
            }),
        );
    });

    it("still limits results to canonical podcasts when includeEmpty is true", async () => {
        await getSearchedPodcasts({ includeEmpty: "true" });

        expect(mockCount).toHaveBeenCalledWith({
            where: publicAttributionWhere,
        });
        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: publicAttributionWhere,
            }),
        );
    });

    it("searches title, author, and description", async () => {
        await getSearchedPodcasts({ q: "standup" });

        expect(mockCount).toHaveBeenCalledWith({
            where: {
                AND: [
                    publicAttributionWhere,
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
                    hosts: [],
                    isFavorite: false,
                },
            ],
            filters: [],
        });
    });

    it("decodes HTML entities in descriptions via the canonical sanitizer", async () => {
        mockCount.mockResolvedValue(1);
        mockFindMany.mockResolvedValue([
            {
                id: 12,
                slug: "good-one",
                title: "Good One",
                authorName: "Vulture",
                websiteUrl: "https://example.com",
                feedUrl: "https://example.com/feed.xml",
                imageUrl: null,
                description: "<p>Comedy interviews &amp; stories</p>",
                _count: { episodes: 42 },
            },
        ]);

        const result = await getSearchedPodcasts({ q: "good" });

        expect(result.data[0].description).toBe("Comedy interviews & stories");
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
        mockCount.mockResolvedValue(500);

        await getSearchedPodcasts({ page: "2", size: "100" });

        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                take: 50,
                skip: 100,
            }),
        );
    });

    it("clamps an out-of-range page to the last page of results", async () => {
        // 45 podcasts at the default size of 20 → pages 0..2; page 99 serves page 2.
        mockCount.mockResolvedValue(45);

        await getSearchedPodcasts({ page: "99" });

        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                take: 20,
                skip: 40,
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
