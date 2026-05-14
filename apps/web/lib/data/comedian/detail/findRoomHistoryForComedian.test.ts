import { describe, it, expect, vi, beforeEach } from "vitest";

const { mockQueryRaw } = vi.hoisted(() => ({
    mockQueryRaw: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: { $queryRaw: mockQueryRaw },
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
    };
}

type AggregatedRow = {
    club_id: number;
    club_name: string;
    club_city: string | null;
    club_state: string | null;
    has_image: boolean;
    play_count: number | bigint;
    last_played_date: Date;
};

function makeRow(over: Partial<AggregatedRow>): AggregatedRow {
    return {
        club_id: 1,
        club_name: "Default Club",
        club_city: "NYC",
        club_state: "NY",
        has_image: false,
        play_count: 1,
        last_played_date: new Date("2024-01-01T00:00:00Z"),
        ...over,
    };
}

function getQueryStrings(): string {
    return mockQueryRaw.mock.calls
        .flatMap((call) => {
            const arg = call[0];
            if (arg && Array.isArray(arg.strings)) {
                return arg.strings as string[];
            }
            return [];
        })
        .join(" ");
}

describe("findRoomHistoryForComedian", () => {
    beforeEach(() => {
        mockQueryRaw.mockReset();
    });

    it("returns an empty array when no comedian is set on the helper", async () => {
        const helper = makeHelper({ comedian: undefined });
        const result = await findRoomHistoryForComedian(helper as never);

        expect(result).toEqual([]);
        expect(mockQueryRaw).not.toHaveBeenCalled();
    });

    it("queries past shows for visible clubs scoped by lineup", async () => {
        mockQueryRaw.mockResolvedValue([]);

        const helper = makeHelper();
        await findRoomHistoryForComedian(helper as never);

        expect(mockQueryRaw).toHaveBeenCalledTimes(1);

        const sql = getQueryStrings();
        expect(sql).toMatch(/FROM "shows"/);
        expect(sql).toMatch(/JOIN "clubs"/);
        expect(sql).toMatch(/JOIN "lineup_items"/);
        expect(sql).toMatch(/JOIN "comedians"/);
        expect(sql).toMatch(/cl\.visible = true/);
        expect(sql).toMatch(/s\.date </);
        expect(sql).toMatch(/GROUP BY/);
        expect(sql).toMatch(/ORDER BY/);
    });

    it("groups distinct shows per (comedian, club) pair and tracks the per-club max date", async () => {
        const cellarMax = new Date("2025-02-14T20:00:00Z");
        const standMax = new Date("2023-09-01T20:00:00Z");

        mockQueryRaw.mockResolvedValue([
            makeRow({
                club_id: 10,
                club_name: "Comedy Cellar",
                club_city: "NYC",
                club_state: "NY",
                has_image: true,
                play_count: 3,
                last_played_date: cellarMax,
            }),
            makeRow({
                club_id: 11,
                club_name: "The Stand",
                club_city: "NYC",
                club_state: "NY",
                has_image: false,
                play_count: 1,
                last_played_date: standMax,
            }),
        ]);

        const result = await findRoomHistoryForComedian(makeHelper() as never);

        expect(result).toHaveLength(2);
        const cellar = result[0];
        expect(cellar.clubId).toBe(10);
        expect(cellar.playCount).toBe(3);
        expect(cellar.lastPlayedDate).toEqual(cellarMax);
        expect(cellar.imageUrl).toBe(
            "https://cdn.example.com/Comedy Cellar.png",
        );

        const stand = result[1];
        expect(stand.clubId).toBe(11);
        expect(stand.playCount).toBe(1);
        expect(stand.lastPlayedDate).toEqual(standMax);
    });

    it("coerces Postgres BigInt counts and timestamptz values into JS Number and Date", async () => {
        const maxDate = new Date("2025-03-01T20:00:00Z");

        mockQueryRaw.mockResolvedValue([
            makeRow({
                club_id: 20,
                club_name: "Reorder Club",
                club_city: null,
                club_state: null,
                has_image: false,
                play_count: BigInt(7),
                last_played_date: maxDate,
            }),
        ]);

        const result = await findRoomHistoryForComedian(makeHelper() as never);

        expect(result).toHaveLength(1);
        expect(result[0].playCount).toBe(7);
        expect(typeof result[0].playCount).toBe("number");
        expect(result[0].lastPlayedDate).toEqual(maxDate);
    });

    it("preserves DB-returned row order (no client-side resort)", async () => {
        // Feed rows in an order that is NOT the function's natural sort
        // (count desc, then date desc) so this test would fail if the
        // implementation silently re-sorted. The SQL string match in the
        // "queries past shows" test covers the DB-side ORDER BY clause.
        mockQueryRaw.mockResolvedValue([
            makeRow({
                club_id: 1,
                club_name: "One Show Club",
                play_count: 1,
                last_played_date: new Date("2024-01-01"),
            }),
            makeRow({
                club_id: 2,
                club_name: "Three Show Club",
                play_count: 3,
                last_played_date: new Date("2024-04-01"),
            }),
            makeRow({
                club_id: 3,
                club_name: "Recent One",
                play_count: 1,
                last_played_date: new Date("2025-01-01"),
            }),
        ]);

        const result = await findRoomHistoryForComedian(makeHelper() as never);

        expect(result.map((r) => r.clubName)).toEqual([
            "One Show Club",
            "Three Show Club",
            "Recent One",
        ]);
    });

    it("emits ORDER BY play_count DESC, last_played_date DESC in the SQL", async () => {
        mockQueryRaw.mockResolvedValue([]);

        await findRoomHistoryForComedian(makeHelper() as never);

        const sql = getQueryStrings();
        expect(sql).toMatch(/ORDER BY play_count DESC, last_played_date DESC/);
    });
});
