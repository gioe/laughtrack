import { describe, it, expect, vi, beforeEach } from "vitest";

const { mockFindMany } = vi.hoisted(() => ({
    mockFindMany: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: { show: { findMany: mockFindMany } },
}));
vi.mock("@/util/imageUtil", () => ({
    buildClubImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.png`,
    ),
}));

import { findRoomHistoryForComedian } from "./findRoomHistoryForComedian";

function makeHelper(
    overrides: Partial<{ comedian: string | undefined }> = {},
) {
    const comedian =
        "comedian" in overrides ? overrides.comedian : "Jane Comic";
    return {
        params: { comedian },
        getLineupItemClause: vi.fn(() => ({ lineupItems: {} })),
    };
}

type ShowRow = {
    id: number;
    date: Date;
    club: {
        id: number;
        name: string;
        city: string | null;
        state: string | null;
        hasImage: boolean;
    };
};

function makeRow(over: Partial<ShowRow> & Pick<ShowRow, "id" | "date">): ShowRow {
    return {
        club: {
            id: 1,
            name: "Default Club",
            city: "NYC",
            state: "NY",
            hasImage: false,
            ...over.club,
        },
        ...over,
    } as ShowRow;
}

describe("findRoomHistoryForComedian", () => {
    beforeEach(() => {
        mockFindMany.mockReset();
    });

    it("returns an empty array when no comedian is set on the helper", async () => {
        const helper = makeHelper({ comedian: undefined });
        const result = await findRoomHistoryForComedian(helper as never);

        expect(result).toEqual([]);
        expect(mockFindMany).not.toHaveBeenCalled();
    });

    it("queries past shows for visible clubs scoped by lineup", async () => {
        mockFindMany.mockResolvedValue([]);

        const helper = makeHelper();
        await findRoomHistoryForComedian(helper as never);

        expect(mockFindMany).toHaveBeenCalledTimes(1);
        const args = mockFindMany.mock.calls[0][0];
        expect(args.where.club).toEqual({ visible: true });
        expect(args.where.date.lt).toBeInstanceOf(Date);
        expect(args.where.lineupItems).toEqual({});
        expect(helper.getLineupItemClause).toHaveBeenCalledTimes(1);
    });

    it("groups distinct shows per (comedian, club) pair and tracks the per-club max date", async () => {
        const cellarA = new Date("2024-01-10T20:00:00Z");
        const cellarB = new Date("2024-06-04T20:00:00Z");
        const cellarC = new Date("2025-02-14T20:00:00Z");
        const standA = new Date("2023-09-01T20:00:00Z");

        mockFindMany.mockResolvedValue([
            makeRow({
                id: 1,
                date: cellarA,
                club: {
                    id: 10,
                    name: "Comedy Cellar",
                    city: "NYC",
                    state: "NY",
                    hasImage: true,
                },
            }),
            makeRow({
                id: 2,
                date: cellarB,
                club: {
                    id: 10,
                    name: "Comedy Cellar",
                    city: "NYC",
                    state: "NY",
                    hasImage: true,
                },
            }),
            makeRow({
                id: 3,
                date: cellarC,
                club: {
                    id: 10,
                    name: "Comedy Cellar",
                    city: "NYC",
                    state: "NY",
                    hasImage: true,
                },
            }),
            makeRow({
                id: 4,
                date: standA,
                club: {
                    id: 11,
                    name: "The Stand",
                    city: "NYC",
                    state: "NY",
                    hasImage: false,
                },
            }),
        ]);

        const result = await findRoomHistoryForComedian(makeHelper() as never);

        expect(result).toHaveLength(2);
        const cellar = result[0];
        expect(cellar.clubId).toBe(10);
        expect(cellar.playCount).toBe(3);
        expect(cellar.lastPlayedDate).toEqual(cellarC);
        expect(cellar.imageUrl).toBe(
            "https://cdn.example.com/Comedy Cellar.png",
        );

        const stand = result[1];
        expect(stand.clubId).toBe(11);
        expect(stand.playCount).toBe(1);
        expect(stand.lastPlayedDate).toEqual(standA);
    });

    it("tracks the per-club max date regardless of row order returned by Prisma", async () => {
        const earlyDate = new Date("2024-01-01T20:00:00Z");
        const midDate = new Date("2024-06-01T20:00:00Z");
        const latestDate = new Date("2025-03-01T20:00:00Z");

        // Return rows in non-ascending order so a naive last-wins
        // implementation would record midDate instead of latestDate.
        mockFindMany.mockResolvedValue([
            makeRow({
                id: 1,
                date: latestDate,
                club: {
                    id: 20,
                    name: "Reorder Club",
                    city: null,
                    state: null,
                    hasImage: false,
                },
            }),
            makeRow({
                id: 2,
                date: earlyDate,
                club: {
                    id: 20,
                    name: "Reorder Club",
                    city: null,
                    state: null,
                    hasImage: false,
                },
            }),
            makeRow({
                id: 3,
                date: midDate,
                club: {
                    id: 20,
                    name: "Reorder Club",
                    city: null,
                    state: null,
                    hasImage: false,
                },
            }),
        ]);

        const result = await findRoomHistoryForComedian(makeHelper() as never);

        expect(result).toHaveLength(1);
        expect(result[0].lastPlayedDate).toEqual(latestDate);
    });

    it("sorts tiles by play count descending, breaking ties by most-recent date", async () => {
        mockFindMany.mockResolvedValue([
            makeRow({
                id: 1,
                date: new Date("2024-01-01"),
                club: {
                    id: 1,
                    name: "One Show Club",
                    city: null,
                    state: null,
                    hasImage: false,
                },
            }),
            makeRow({
                id: 2,
                date: new Date("2024-02-01"),
                club: {
                    id: 2,
                    name: "Three Show Club",
                    city: null,
                    state: null,
                    hasImage: false,
                },
            }),
            makeRow({
                id: 3,
                date: new Date("2024-03-01"),
                club: {
                    id: 2,
                    name: "Three Show Club",
                    city: null,
                    state: null,
                    hasImage: false,
                },
            }),
            makeRow({
                id: 4,
                date: new Date("2024-04-01"),
                club: {
                    id: 2,
                    name: "Three Show Club",
                    city: null,
                    state: null,
                    hasImage: false,
                },
            }),
            makeRow({
                id: 5,
                date: new Date("2025-01-01"),
                club: {
                    id: 3,
                    name: "Recent One",
                    city: null,
                    state: null,
                    hasImage: false,
                },
            }),
        ]);

        const result = await findRoomHistoryForComedian(makeHelper() as never);

        expect(result.map((r) => r.clubName)).toEqual([
            "Three Show Club",
            "Recent One",
            "One Show Club",
        ]);
    });
});
