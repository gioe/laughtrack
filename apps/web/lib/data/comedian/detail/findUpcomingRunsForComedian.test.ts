import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/db", () => ({
    db: {
        comedian: { findUnique: vi.fn() },
        show: { findMany: vi.fn() },
    },
}));
vi.mock("@/util/comedian/comedianUtil", () => ({
    filterAndMapLineupItems: vi.fn(() => []),
}));
vi.mock("@/util/imageUtil", () => ({
    buildClubImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.jpg`,
    ),
}));
vi.mock("@/util/ticket/ticketUtil", () => ({
    mapTickets: vi.fn((tickets) => tickets),
}));

import { db } from "@/lib/db";
import { findUpcomingRunsForComedian } from "./findUpcomingRunsForComedian";

const mockFindUnique = vi.mocked(db.comedian.findUnique);
const mockFindMany = vi.mocked(db.show.findMany);

beforeEach(() => {
    vi.clearAllMocks();
    mockFindUnique.mockResolvedValue({
        id: 123,
        uuid: "comedian-uuid",
    } as never);
});

describe("findUpcomingRunsForComedian", () => {
    it("groups consecutive same-club shows into runs and splits re-entries", async () => {
        mockFindMany.mockResolvedValue([
            makeShow({ id: 1, clubId: 10, clubName: "A Club" }),
            makeShow({ id: 2, clubId: 10, clubName: "A Club" }),
            makeShow({ id: 3, clubId: 20, clubName: "B Club" }),
            makeShow({ id: 4, clubId: 10, clubName: "A Club" }),
        ] as never);

        const runs = await findUpcomingRunsForComedian(123, {
            timezone: "America/New_York",
        });

        expect(runs.map((run) => run.clubID)).toEqual([10, 20, 10]);
        expect(runs.map((run) => run.shows.map((show) => show.id))).toEqual([
            [1, 2],
            [3],
            [4],
        ]);
    });

    it("filters by club, location, and date before grouping over the full result set", async () => {
        mockFindMany.mockResolvedValue([] as never);

        await findUpcomingRunsForComedian(123, {
            club: "cellar",
            location: "New York",
            date: "2026-07-01",
            timezone: "America/New_York",
        });

        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: expect.objectContaining({
                    club: expect.objectContaining({
                        name: expect.objectContaining({
                            contains: "cellar",
                        }),
                        OR: expect.arrayContaining([
                            {
                                address: expect.objectContaining({
                                    contains: "New York",
                                }),
                            },
                            {
                                city: expect.objectContaining({
                                    contains: "New York",
                                }),
                            },
                            {
                                state: expect.objectContaining({
                                    contains: "New York",
                                }),
                            },
                            {
                                country: expect.objectContaining({
                                    contains: "New York",
                                }),
                            },
                            {
                                zipCode: expect.objectContaining({
                                    contains: "New York",
                                }),
                            },
                        ]),
                    }),
                }),
                orderBy: [{ date: "asc" }, { id: "asc" }],
            }),
        );
    });
});

function makeShow({
    id,
    clubId,
    clubName,
}: {
    id: number;
    clubId: number;
    clubName: string;
}) {
    return {
        id,
        name: `Show ${id}`,
        date: new Date(`2026-07-0${id}T23:00:00.000Z`),
        description: null,
        room: null,
        tickets: [],
        club: {
            id: clubId,
            name: clubName,
            address: "117 MacDougal St, New York, NY",
            city: "New York",
            state: "NY",
            country: "US",
            zipCode: "10012",
            hasImage: true,
            timezone: "America/New_York",
        },
        lineupItems: [],
    };
}
