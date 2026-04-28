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

const mockFindFirst = vi.mocked(db.comedian.findFirst);

function makeHelper(
    slug: string | undefined = "alice-smith",
    profileId: string | undefined = undefined,
): QueryHelper {
    return {
        getSlug: () => slug,
        getProfileId: () => profileId,
    } as unknown as QueryHelper;
}

function makeComedianRow(
    overrides: Partial<{
        id: number;
        uuid: string;
        name: string;
        bio: string | null;
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
        parentComedianId: number | null;
        songkickId: string | null;
        bandsintownId: string | null;
        websiteDiscoverySource: string | null;
        websiteLastScraped: Date | null;
        websiteScrapeStrategy: string | null;
        websiteScrapingUrl: string | null;
        websiteConfidence: string | null;
        websiteScrapingUrlConfidence: string | null;
        lineupItems: {
            id: number;
            show: {
                id: number;
                date: Date;
                name: string | null;
                club: {
                    name: string;
                    city: string | null;
                    state: string | null;
                };
            };
        }[];
        favoriteComedians: { id: number }[];
    }> = {},
) {
    return {
        id: 1,
        uuid: "uuid-1",
        name: "Alice Smith",
        bio: null,
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
        lineupItems: [
            {
                id: 10,
                show: {
                    id: 101,
                    date: new Date("2026-05-01T20:00:00.000Z"),
                    name: "Friday Night",
                    club: {
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
                        name: "Comedy Club",
                        city: "Austin",
                        state: "TX",
                    },
                },
            },
        ],
        favoriteComedians: [],
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("findComedianByName", () => {
    describe("show_count", () => {
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

            expect(result.show_count).toBe(5);
        });

        it("is 0 when lineupItems is empty", async () => {
            const row = makeComedianRow({ lineupItems: [] });
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(makeHelper());

            expect(result.show_count).toBe(0);
        });

        it("maps upcoming show city data into dates for header city counts", async () => {
            const row = makeComedianRow();
            mockFindFirst.mockResolvedValue(row);

            const result = await findComedianByName(makeHelper());

            expect(result.dates).toEqual([
                {
                    id: 101,
                    date: new Date("2026-05-01T20:00:00.000Z"),
                    name: "Friday Night",
                    clubName: "Comedy Club",
                    clubCity: "Austin",
                    clubState: "TX",
                    imageUrl: "https://cdn.example.com/Alice Smith.png",
                },
                {
                    id: 102,
                    date: new Date("2026-05-02T20:00:00.000Z"),
                    name: null,
                    clubName: "Laugh Room",
                    clubCity: "Dallas",
                    clubState: "TX",
                    imageUrl: "https://cdn.example.com/Alice Smith.png",
                },
                {
                    id: 103,
                    date: new Date("2026-05-03T20:00:00.000Z"),
                    name: "Late Show",
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
