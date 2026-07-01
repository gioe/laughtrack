import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/db", () => ({
    db: {
        comedian: {
            groupBy: vi.fn(),
        },
        club: {
            findMany: vi.fn(),
        },
    },
}));

import {
    getComedianHomeClubFilters,
    MIN_COMEDIANS_PER_HOME_CLUB,
} from "./getComedianHomeClubFilters";
import { db } from "@/lib/db";

const mockGroupBy = vi.mocked(db.comedian.groupBy);
const mockFindMany = vi.mocked(db.club.findMany);

function group(homeClubId: number | null, n: number) {
    return { homeClubId, _count: { _all: n } };
}

describe("getComedianHomeClubFilters", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("returns [] and skips the name lookup when no comedian has a home club", async () => {
        mockGroupBy.mockResolvedValue([] as never);

        expect(await getComedianHomeClubFilters()).toEqual([]);
        expect(mockFindMany).not.toHaveBeenCalled();
    });

    it("builds club-id values with club-name labels, ordered by count desc", async () => {
        mockGroupBy.mockResolvedValue([
            group(10, 4),
            group(20, 12),
            group(30, 7),
        ] as never);
        mockFindMany.mockResolvedValue([
            { id: 10, name: "The Setup" },
            { id: 20, name: "Comedy Store" },
            { id: 30, name: "Laugh Factory" },
        ] as never);

        const result = await getComedianHomeClubFilters();

        expect(result).toEqual([
            { value: "20", label: "Comedy Store", count: 12 },
            { value: "30", label: "Laugh Factory", count: 7 },
            { value: "10", label: "The Setup", count: 4 },
        ]);
        // Only the qualifying club ids are looked up for names.
        expect(mockFindMany).toHaveBeenCalledWith({
            where: { id: { in: [10, 20, 30] } },
            select: { id: true, name: true },
        });
    });

    it("drops clubs below the minimum-count threshold before the name lookup", async () => {
        mockGroupBy.mockResolvedValue([
            group(1, MIN_COMEDIANS_PER_HOME_CLUB),
            group(2, MIN_COMEDIANS_PER_HOME_CLUB - 1),
        ] as never);
        mockFindMany.mockResolvedValue([{ id: 1, name: "Kept Club" }] as never);

        const result = await getComedianHomeClubFilters();

        expect(result.map((r) => r.value)).toEqual(["1"]);
        expect(mockFindMany).toHaveBeenCalledWith({
            where: { id: { in: [1] } },
            select: { id: true, name: true },
        });
    });

    it("returns [] and skips the name lookup when every group is below threshold", async () => {
        mockGroupBy.mockResolvedValue([
            group(1, MIN_COMEDIANS_PER_HOME_CLUB - 1),
        ] as never);

        expect(await getComedianHomeClubFilters()).toEqual([]);
        expect(mockFindMany).not.toHaveBeenCalled();
    });

    it("falls back to a placeholder label when a club name is missing", async () => {
        mockGroupBy.mockResolvedValue([group(42, 5)] as never);
        mockFindMany.mockResolvedValue([] as never);

        const result = await getComedianHomeClubFilters();

        expect(result).toEqual([{ value: "42", label: "Club 42", count: 5 }]);
    });

    it("breaks count ties alphabetically by label", async () => {
        mockGroupBy.mockResolvedValue([group(1, 5), group(2, 5)] as never);
        mockFindMany.mockResolvedValue([
            { id: 1, name: "Zebra Room" },
            { id: 2, name: "Alpha Room" },
        ] as never);

        const result = await getComedianHomeClubFilters();

        expect(result.map((r) => r.label)).toEqual([
            "Alpha Room",
            "Zebra Room",
        ]);
    });
});
