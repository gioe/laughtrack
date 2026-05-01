import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/db", () => ({
    db: { show: { findMany: vi.fn() } },
}));
vi.mock("@/util/imageUtil", () => ({
    buildClubImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.jpg`,
    ),
}));
vi.mock("@/util/ticket/ticketUtil", () => ({
    mapTickets: vi.fn((tickets: any[]) =>
        tickets.map((t) => ({
            price: t.price ? t.price.toFixed(2) : null,
            purchaseUrl: t.purchaseUrl,
            type: t.type,
            soldOut: t.soldOut,
        })),
    ),
}));
vi.mock("@/util/distanceUtil", () => ({
    computeDistanceMiles: vi.fn(
        (_fromZip: string | undefined, toZip: string) => {
            const distances: Record<string, number> = {
                "10001": 18,
                "10003": 4,
                "10011": 4,
            };
            return distances[toZip] ?? null;
        },
    ),
}));
vi.mock("@/util/comedian/comedianUtil", () => ({
    filterAndMapLineupItems: vi.fn((items: any[]) =>
        items.map((item) => ({
            id: item.comedian.id,
            uuid: item.comedian.uuid,
            name: item.comedian.name,
            imageUrl: item.comedian.hasImage
                ? `https://cdn.example.com/${item.comedian.name}.png`
                : "",
            show_count: item.comedian._count?.lineupItems,
            isFavorite: false,
            isAlias: false,
        })),
    ),
}));

import { findShowsForHome } from "./findShowsForHome";
import { db } from "@/lib/db";

const mockFindMany = vi.mocked(db.show.findMany);

function makeTicket(
    overrides: Partial<{
        price: number | null;
        soldOut: boolean;
        purchaseUrl: string | null;
        type: string;
    }> = {},
) {
    return {
        price: 20,
        soldOut: false,
        purchaseUrl: "https://tickets.example.com",
        type: "general",
        ...overrides,
    };
}

function makeLineupItem(
    overrides: Partial<{
        id: number;
        uuid: string;
        name: string;
        hasImage: boolean;
        showCount: number;
    }> = {},
) {
    const { showCount, ...comedianOverrides } = overrides;
    return {
        comedian: {
            id: 1,
            uuid: "uuid-1",
            name: "Test Comedian",
            hasImage: true,
            _count: { lineupItems: showCount ?? 1 },
            parentComedian: null,
            taggedComedians: [],
            ...comedianOverrides,
        },
    };
}

function makeShowRow(
    overrides: Partial<{
        id: number;
        name: string;
        date: Date;
        tickets: ReturnType<typeof makeTicket>[];
        popularity: number;
        club: {
            name: string;
            address: string;
            zipCode?: string;
            hasImage?: boolean;
            timezone?: string | null;
        };
        lineupItems: ReturnType<typeof makeLineupItem>[];
    }> = {},
) {
    return {
        id: 1,
        name: "Test Show",
        date: new Date("2026-06-01"),
        popularity: 0,
        tickets: [makeTicket()],
        club: {
            name: "Laugh Factory",
            address: "8001 Sunset Blvd",
            zipCode: "90046",
            hasImage: true,
            timezone: "America/Los_Angeles",
        },
        lineupItems: [makeLineupItem()],
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("findShowsForHome", () => {
    describe("soldOut computation", () => {
        it("returns soldOut=true when all tickets are soldOut", async () => {
            const row = makeShowRow({
                tickets: [
                    makeTicket({ soldOut: true }),
                    makeTicket({ soldOut: true }),
                ],
            });
            mockFindMany.mockResolvedValue([row] as any);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].soldOut).toBe(true);
        });

        it("returns soldOut=false when at least one ticket is not soldOut", async () => {
            const row = makeShowRow({
                tickets: [
                    makeTicket({ soldOut: true }),
                    makeTicket({ soldOut: false }),
                ],
            });
            mockFindMany.mockResolvedValue([row] as any);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].soldOut).toBe(false);
        });

        it("returns soldOut=false when there are no tickets", async () => {
            const row = makeShowRow({ tickets: [] });
            mockFindMany.mockResolvedValue([row] as any);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].soldOut).toBe(false);
        });

        it("returns soldOut=false when single ticket is not soldOut", async () => {
            const row = makeShowRow({
                tickets: [makeTicket({ soldOut: false })],
            });
            mockFindMany.mockResolvedValue([row] as any);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].soldOut).toBe(false);
        });
    });

    describe("lineup tag filter (userFacing=false excluded)", () => {
        it("passes lineupItems through filterAndMapLineupItems", async () => {
            const { filterAndMapLineupItems } = await import(
                "@/util/comedian/comedianUtil"
            );
            const mockFilter = vi.mocked(filterAndMapLineupItems);

            const lineupItems = [
                makeLineupItem(),
                makeLineupItem({ id: 2, uuid: "uuid-2", name: "Comedian B" }),
            ];
            const row = makeShowRow({ lineupItems });
            mockFindMany.mockResolvedValue([row] as any);

            await findShowsForHome({}, { date: "asc" });

            expect(mockFilter).toHaveBeenCalledWith(lineupItems);
        });

        it("returns empty lineup when filterAndMapLineupItems returns empty array", async () => {
            const { filterAndMapLineupItems } = await import(
                "@/util/comedian/comedianUtil"
            );
            vi.mocked(filterAndMapLineupItems).mockReturnValueOnce([]);

            const row = makeShowRow({ lineupItems: [makeLineupItem()] });
            mockFindMany.mockResolvedValue([row] as any);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].lineup).toEqual([]);
        });

        it("returns mapped lineup items from filterAndMapLineupItems", async () => {
            const { filterAndMapLineupItems } = await import(
                "@/util/comedian/comedianUtil"
            );
            const mappedItem = {
                id: 99,
                uuid: "uuid-99",
                name: "Filtered Comic",
                imageUrl: "https://cdn.example.com/Filtered Comic.png",
                hasImage: true,
                show_count: 12,
                isFavorite: false,
                isAlias: false,
            };
            vi.mocked(filterAndMapLineupItems).mockReturnValueOnce([
                mappedItem,
            ]);

            const row = makeShowRow({ lineupItems: [makeLineupItem()] });
            mockFindMany.mockResolvedValue([row] as any);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].lineup).toEqual([mappedItem]);
        });
    });

    describe("DTO field mapping", () => {
        it("maps clubName, address, and id from the DB row", async () => {
            const row = makeShowRow({
                id: 42,
                name: "Friday Night Comedy",
                club: { name: "Comedy Cellar", address: "117 Macdougal St" },
            });
            mockFindMany.mockResolvedValue([row] as any);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result).toHaveLength(1);
            const dto = result[0];
            expect(dto.id).toBe(42);
            expect(dto.name).toBe("Friday Night Comedy");
            expect(dto.clubName).toBe("Comedy Cellar");
            expect(dto.address).toBe("117 Macdougal St");
        });

        it("uses the most popular lineup comedian image when one is available", async () => {
            const row = makeShowRow({
                lineupItems: [
                    makeLineupItem({
                        id: 1,
                        uuid: "opener",
                        name: "Opener Comic",
                        showCount: 4,
                    }),
                    makeLineupItem({
                        id: 2,
                        uuid: "headliner",
                        name: "Headliner Comic",
                        showCount: 80,
                    }),
                ],
            });
            mockFindMany.mockResolvedValue([row] as any);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].imageUrl).toBe(
                "https://cdn.example.com/Headliner Comic.png",
            );
        });

        it("falls back to the club image when the lineup has no comedian image", async () => {
            const row = makeShowRow({
                club: { name: "Comedy Cellar", address: "117 Macdougal St" },
                lineupItems: [
                    makeLineupItem({
                        id: 1,
                        uuid: "comic-without-image",
                        name: "Comic Without Image",
                        hasImage: false,
                    }),
                ],
            });
            mockFindMany.mockResolvedValue([row] as any);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].imageUrl).toBe(
                "https://cdn.example.com/Comedy Cellar.jpg",
            );
        });

        it("sorts ZIP-scoped home shows by proximity and lineup popularity", async () => {
            const farPopular = makeShowRow({
                id: 1,
                club: {
                    name: "Far Club",
                    address: "123 Far St",
                    zipCode: "10001",
                },
                lineupItems: [
                    makeLineupItem({
                        name: "Far Headliner",
                        showCount: 500,
                    }),
                ],
            });
            const nearLessPopular = makeShowRow({
                id: 2,
                club: {
                    name: "Near Club",
                    address: "123 Near St",
                    zipCode: "10003",
                },
                lineupItems: [
                    makeLineupItem({
                        name: "Near Opener",
                        showCount: 5,
                    }),
                ],
            });
            const nearMorePopular = makeShowRow({
                id: 3,
                club: {
                    name: "Nearer Club",
                    address: "456 Near St",
                    zipCode: "10011",
                },
                lineupItems: [
                    makeLineupItem({
                        name: "Near Headliner",
                        showCount: 50,
                    }),
                ],
            });
            mockFindMany.mockResolvedValue([
                farPopular,
                nearLessPopular,
                nearMorePopular,
            ] as any);

            const result = await findShowsForHome({}, { date: "asc" }, 2, {
                zipCode: "10801",
                sortByHomeRelevance: true,
            });

            expect(result.map((show) => show.id)).toEqual([3, 2]);
            expect(result.map((show) => show.distanceMiles)).toEqual([4, 4]);
        });

        it("passes tickets through mapTickets", async () => {
            const { mapTickets } = await import("@/util/ticket/ticketUtil");
            const mockMap = vi.mocked(mapTickets);

            const tickets = [makeTicket({ price: 25, type: "vip" })];
            const row = makeShowRow({ tickets });
            mockFindMany.mockResolvedValue([row] as any);

            await findShowsForHome({}, { date: "asc" });

            expect(mockMap).toHaveBeenCalledWith(tickets);
        });

        it("includes the date field from the DB row", async () => {
            const date = new Date("2026-07-04");
            const row = makeShowRow({ date });
            mockFindMany.mockResolvedValue([row] as any);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].date).toEqual(date);
        });

        it("maps club.timezone onto the returned DTO", async () => {
            const row = makeShowRow({
                club: {
                    name: "Flappers",
                    address: "102 E Magnolia Blvd",
                    timezone: "America/Los_Angeles",
                },
            });
            mockFindMany.mockResolvedValue([row] as any);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].timezone).toBe("America/Los_Angeles");
        });

        it("returns null timezone when the club has no timezone configured", async () => {
            const row = makeShowRow({
                club: {
                    name: "Carry On",
                    address: "123 Midtown",
                    timezone: null,
                },
            });
            mockFindMany.mockResolvedValue([row] as any);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].timezone).toBeNull();
        });

        it("selects club.timezone from the database", async () => {
            mockFindMany.mockResolvedValue([] as any);

            await findShowsForHome({}, { date: "asc" });

            const call = mockFindMany.mock.calls[0][0] as {
                select: { club: { select: Record<string, unknown> } };
            };
            expect(call.select.club.select.timezone).toBe(true);
        });

        it("returns an empty array when the DB returns no rows", async () => {
            mockFindMany.mockResolvedValue([] as any);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result).toEqual([]);
        });
    });

    describe("LIMIT=8 cap (take parameter)", () => {
        it("calls findMany with take=8 by default", async () => {
            mockFindMany.mockResolvedValue([] as any);

            await findShowsForHome({}, { date: "asc" });

            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ take: 8 }),
            );
        });

        it("calls findMany with a custom take when provided", async () => {
            mockFindMany.mockResolvedValue([] as any);

            await findShowsForHome({}, { date: "asc" }, 4);

            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ take: 4 }),
            );
        });

        it("passes where and orderBy through to findMany", async () => {
            mockFindMany.mockResolvedValue([] as any);
            const where = { date: { gte: new Date() } };
            const orderBy = { date: "asc" as const };

            await findShowsForHome(where, orderBy);

            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ where, orderBy }),
            );
        });
    });
});
