import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

vi.mock("./findShowsForHome", () => ({
    findShowsForHome: vi.fn(),
}));
vi.mock("@/util/location/resolveNearbyZips", () => ({
    resolveNearbyZips: vi.fn(() => ["10801", "10803"]),
}));

import { findShowsForHome } from "./findShowsForHome";
import { resolveNearbyZips } from "@/util/location/resolveNearbyZips";
import { getFavoriteComedianShows } from "./getFavoriteComedianShows";

const mockFindShowsForHome = vi.mocked(findShowsForHome);
const mockResolveNearbyZips = vi.mocked(resolveNearbyZips);

beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-06-01T12:00:00.000Z"));
    vi.clearAllMocks();
});

afterEach(() => {
    vi.useRealTimers();
});

describe("getFavoriteComedianShows", () => {
    it("returns an empty rail without querying when no profile id is provided", async () => {
        await expect(getFavoriteComedianShows(null)).resolves.toEqual([]);

        expect(mockFindShowsForHome).not.toHaveBeenCalled();
    });

    it("finds upcoming visible shows whose lineup includes a favorited canonical comedian", async () => {
        const shows = [{ id: 7, name: "Favorite Comic Night" }];
        mockFindShowsForHome.mockResolvedValue(shows as never);

        await expect(getFavoriteComedianShows("profile-1")).resolves.toBe(
            shows,
        );

        expect(mockFindShowsForHome).toHaveBeenCalledWith(
            {
                date: { gte: new Date("2026-06-01T12:00:00.000Z") },
                club: { visible: true },
                lineupItems: {
                    some: {
                        comedian: {
                            visible: true,
                            OR: [
                                {
                                    favoriteComedians: {
                                        some: { profileId: "profile-1" },
                                    },
                                },
                                {
                                    parentComedian: {
                                        visible: true,
                                        favoriteComedians: {
                                            some: {
                                                profileId: "profile-1",
                                            },
                                        },
                                    },
                                },
                            ],
                        },
                    },
                },
            },
            [{ popularity: "desc" }, { date: "asc" }, { id: "asc" }],
            8,
            { profileId: "profile-1" },
        );
    });

    it("filters followed-comedian shows to the supplied ZIP radius", async () => {
        mockFindShowsForHome.mockResolvedValue([]);

        await getFavoriteComedianShows("profile-1", "10801", 50);

        expect(mockResolveNearbyZips).toHaveBeenCalledWith("10801", 50);
        expect(mockFindShowsForHome).toHaveBeenCalledWith(
            {
                date: { gte: new Date("2026-06-01T12:00:00.000Z") },
                club: {
                    visible: true,
                    zipCode: { in: ["10801", "10803"] },
                },
                lineupItems: {
                    some: {
                        comedian: {
                            visible: true,
                            OR: [
                                {
                                    favoriteComedians: {
                                        some: { profileId: "profile-1" },
                                    },
                                },
                                {
                                    parentComedian: {
                                        visible: true,
                                        favoriteComedians: {
                                            some: {
                                                profileId: "profile-1",
                                            },
                                        },
                                    },
                                },
                            ],
                        },
                    },
                },
            },
            [{ popularity: "desc" }, { date: "asc" }, { id: "asc" }],
            8,
            { profileId: "profile-1", zipCode: "10801" },
        );
    });

    it("preserves global followed-comedian results without a usable ZIP", async () => {
        const shows = [{ id: 8, name: "Global Favorite Comic Night" }];
        mockFindShowsForHome.mockResolvedValue(shows as never);

        await expect(
            getFavoriteComedianShows("profile-1", "not-a-zip", 50),
        ).resolves.toBe(shows);

        expect(mockResolveNearbyZips).not.toHaveBeenCalled();
        expect(mockFindShowsForHome).toHaveBeenCalledWith(
            expect.objectContaining({ club: { visible: true } }),
            [{ popularity: "desc" }, { date: "asc" }, { id: "asc" }],
            8,
            { profileId: "profile-1" },
        );
    });

    describe("tags emission (TASK-2567)", () => {
        // Wrapper is pure delegation to findShowsForHome; comprehensive
        // tags-emission tests (PUBLIC filter, null filtering, empty case)
        // live on findShowsForHome.test.ts. This block guards against a
        // future regression that adds a mapper here which strips tags.

        it("passes tags through from findShowsForHome unchanged", async () => {
            const tagged = [
                { id: 1, tags: [{ slug: "open mic", name: "Open Mic" }] },
            ];
            mockFindShowsForHome.mockResolvedValue(tagged as never);

            const result = await getFavoriteComedianShows("profile-1");

            expect(result).toBe(tagged);
            expect(result[0].tags).toEqual([
                { slug: "open mic", name: "Open Mic" },
            ]);
        });
    });
});
