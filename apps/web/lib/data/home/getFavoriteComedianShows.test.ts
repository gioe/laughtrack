import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

vi.mock("./findShowsForHome", () => ({
    findShowsForHome: vi.fn(),
}));

import { findShowsForHome } from "./findShowsForHome";
import { getFavoriteComedianShows } from "./getFavoriteComedianShows";

const mockFindShowsForHome = vi.mocked(findShowsForHome);

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

    it("finds upcoming visible shows whose lineup includes a favorited comedian", async () => {
        const shows = [{ id: 7, name: "Favorite Comic Night" }];
        mockFindShowsForHome.mockResolvedValue(shows as any);

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
                            favoriteComedians: {
                                some: { profileId: "profile-1" },
                            },
                        },
                    },
                },
            },
            [{ date: "asc" }, { popularity: "desc" }],
            8,
        );
    });
});
