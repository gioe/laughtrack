import { describe, it, expect, vi, beforeEach } from "vitest";

type TicketInput = {
    price?: number | null;
    purchaseUrl?: string | null;
    type?: string;
    soldOut?: boolean;
};

type LineupInput = {
    comedian: {
        id: number;
        uuid: string;
        name: string;
        hasImage: boolean;
        _count?: { lineupItems?: number };
    };
};

type TaggedShowInput = { tag: { slug: string | null; name: string | null } };

vi.mock("@/lib/db", () => ({
    db: { show: { findMany: vi.fn() } },
}));
vi.mock("@/util/imageUtil", () => ({
    buildClubImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.jpg`,
    ),
}));
vi.mock("@/util/ticket/ticketUtil", () => ({
    mapTickets: vi.fn((tickets: TicketInput[]) =>
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
    filterAndMapLineupItems: vi.fn((items: LineupInput[]) =>
        items.map((item) => ({
            id: item.comedian.id,
            uuid: item.comedian.uuid,
            name: item.comedian.name,
            imageUrl: item.comedian.hasImage
                ? `https://cdn.example.com/${item.comedian.name}.png`
                : "",
            showCount: item.comedian._count?.lineupItems,
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
            id?: number;
            name: string;
            address: string;
            zipCode?: string;
            hasImage?: boolean;
            timezone?: string | null;
        };
        lineupItems: ReturnType<typeof makeLineupItem>[];
        taggedShows: TaggedShowInput[];
    }> = {},
) {
    return {
        id: 1,
        name: "Test Show",
        date: new Date("2026-06-01"),
        popularity: 0,
        tickets: [makeTicket()],
        club: {
            id: 88,
            name: "Laugh Factory",
            address: "8001 Sunset Blvd",
            zipCode: "90046",
            hasImage: true,
            timezone: "America/Los_Angeles",
        },
        lineupItems: [makeLineupItem()],
        taggedShows: [],
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
            mockFindMany.mockResolvedValue([row] as never);

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
            mockFindMany.mockResolvedValue([row] as never);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].soldOut).toBe(false);
        });

        it("returns soldOut=false when there are no tickets", async () => {
            const row = makeShowRow({ tickets: [] });
            mockFindMany.mockResolvedValue([row] as never);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].soldOut).toBe(false);
        });

        it("returns soldOut=false when single ticket is not soldOut", async () => {
            const row = makeShowRow({
                tickets: [makeTicket({ soldOut: false })],
            });
            mockFindMany.mockResolvedValue([row] as never);

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
            mockFindMany.mockResolvedValue([row] as never);

            await findShowsForHome({}, { date: "asc" });

            expect(mockFilter).toHaveBeenCalledWith(lineupItems);
        });

        it("returns empty lineup when filterAndMapLineupItems returns empty array", async () => {
            const { filterAndMapLineupItems } = await import(
                "@/util/comedian/comedianUtil"
            );
            vi.mocked(filterAndMapLineupItems).mockReturnValueOnce([]);

            const row = makeShowRow({ lineupItems: [makeLineupItem()] });
            mockFindMany.mockResolvedValue([row] as never);

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
                showCount: 12,
                isFavorite: false,
                isAlias: false,
            };
            vi.mocked(filterAndMapLineupItems).mockReturnValueOnce([
                mappedItem,
            ]);

            const row = makeShowRow({ lineupItems: [makeLineupItem()] });
            mockFindMany.mockResolvedValue([row] as never);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].lineup).toEqual([mappedItem]);
        });
    });

    describe("DTO field mapping", () => {
        it("maps clubID, clubName, address, and id from the DB row", async () => {
            const row = makeShowRow({
                id: 42,
                name: "Friday Night Comedy",
                club: {
                    id: 117,
                    name: "Comedy Cellar",
                    address: "117 Macdougal St",
                },
            });
            mockFindMany.mockResolvedValue([row] as never);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result).toHaveLength(1);
            const dto = result[0];
            expect(dto.id).toBe(42);
            expect(dto.name).toBe("Friday Night Comedy");
            expect(dto.clubId).toBe(117);
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
            mockFindMany.mockResolvedValue([row] as never);

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
            mockFindMany.mockResolvedValue([row] as never);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].imageUrl).toBe(
                "https://cdn.example.com/Comedy Cellar.jpg",
            );
        });

        it("sorts ZIP-scoped home shows by time, show popularity, and lineup popularity", async () => {
            const laterPopular = makeShowRow({
                id: 1,
                date: new Date("2026-06-02T20:00:00Z"),
                popularity: 500,
                club: {
                    name: "Later Club",
                    address: "123 Later St",
                    zipCode: "10001",
                },
                lineupItems: [
                    makeLineupItem({
                        name: "Later Headliner",
                        showCount: 500,
                    }),
                ],
            });
            const earlyLessPopular = makeShowRow({
                id: 2,
                date: new Date("2026-06-01T20:00:00Z"),
                popularity: 10,
                club: {
                    name: "Early Club",
                    address: "123 Early St",
                    zipCode: "10003",
                },
                lineupItems: [
                    makeLineupItem({
                        name: "Early Opener",
                        showCount: 5,
                    }),
                ],
            });
            const earlyMorePopular = makeShowRow({
                id: 3,
                date: new Date("2026-06-01T20:00:00Z"),
                popularity: 20,
                club: {
                    name: "Early Popular Club",
                    address: "456 Early St",
                    zipCode: "10011",
                },
                lineupItems: [
                    makeLineupItem({
                        name: "Early Popular Opener",
                        showCount: 5,
                    }),
                ],
            });
            const earlySameShowMoreLineup = makeShowRow({
                id: 4,
                date: new Date("2026-06-01T20:00:00Z"),
                popularity: 20,
                club: {
                    name: "Early Lineup Club",
                    address: "789 Early St",
                    zipCode: "10003",
                },
                lineupItems: [
                    makeLineupItem({
                        name: "Early Lineup Headliner",
                        showCount: 50,
                    }),
                ],
            });
            mockFindMany.mockResolvedValue([
                laterPopular,
                earlyLessPopular,
                earlyMorePopular,
                earlySameShowMoreLineup,
            ] as never);

            const result = await findShowsForHome({}, { date: "asc" }, 3, {
                zipCode: "10801",
                sortByHomeRelevance: true,
            });

            expect(result.map((show) => show.id)).toEqual([4, 3, 2]);
        });

        it("passes tickets through mapTickets", async () => {
            const { mapTickets } = await import("@/util/ticket/ticketUtil");
            const mockMap = vi.mocked(mapTickets);

            const tickets = [makeTicket({ price: 25, type: "vip" })];
            const row = makeShowRow({ tickets });
            mockFindMany.mockResolvedValue([row] as never);

            await findShowsForHome({}, { date: "asc" });

            expect(mockMap).toHaveBeenCalledWith(tickets);
        });

        it("includes the date field from the DB row", async () => {
            const date = new Date("2026-07-04");
            const row = makeShowRow({ date });
            mockFindMany.mockResolvedValue([row] as never);

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
            mockFindMany.mockResolvedValue([row] as never);

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
            mockFindMany.mockResolvedValue([row] as never);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].timezone).toBeNull();
        });

        it("selects club.timezone from the database", async () => {
            mockFindMany.mockResolvedValue([] as never);

            await findShowsForHome({}, { date: "asc" });

            const call = mockFindMany.mock.calls[0][0] as {
                select: { club: { select: Record<string, unknown> } };
            };
            expect(call.select.club.select.timezone).toBe(true);
        });

        it("selects club.id from the database", async () => {
            mockFindMany.mockResolvedValue([] as never);

            await findShowsForHome({}, { date: "asc" });

            const call = mockFindMany.mock.calls[0][0] as {
                select: { club: { select: Record<string, unknown> } };
            };
            expect(call.select.club.select.id).toBe(true);
        });

        it("returns an empty array when the DB returns no rows", async () => {
            mockFindMany.mockResolvedValue([] as never);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result).toEqual([]);
        });
    });

    describe("LIMIT=8 cap (take parameter)", () => {
        it("calls findMany with take=8 by default", async () => {
            mockFindMany.mockResolvedValue([] as never);

            await findShowsForHome({}, { date: "asc" });

            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ take: 8 }),
            );
        });

        it("calls findMany with a custom take when provided", async () => {
            mockFindMany.mockResolvedValue([] as never);

            await findShowsForHome({}, { date: "asc" }, 4);

            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ take: 4 }),
            );
        });

        it("passes where and orderBy through to findMany", async () => {
            mockFindMany.mockResolvedValue([] as never);
            const where = { date: { gte: new Date() } };
            const orderBy = { date: "asc" as const };

            await findShowsForHome(where, orderBy);

            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ where, orderBy }),
            );
        });
    });

    describe("tags emission (TASK-2567)", () => {
        // Home-shelf and related-shows Show responses now carry `tags` so
        // iOS ShowRow can run tag-based open-mic detection without falling
        // back to the name heuristic. PUBLIC-only filter matches the show
        // detail and findShowsWithCount endpoints.

        it("maps row.taggedShows[].tag to a flat tags array of {slug, name}", async () => {
            const row = makeShowRow({
                taggedShows: [
                    { tag: { slug: "open mic", name: "Open Mic" } },
                    { tag: { slug: "weekly", name: "Weekly" } },
                ],
            });
            mockFindMany.mockResolvedValue([row] as never);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].tags).toEqual([
                { slug: "open mic", name: "Open Mic" },
                { slug: "weekly", name: "Weekly" },
            ]);
        });

        it("returns an empty tags array when the show has no tagged_shows rows", async () => {
            const row = makeShowRow({ taggedShows: [] });
            mockFindMany.mockResolvedValue([row] as never);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].tags).toEqual([]);
        });

        it("constrains the taggedShows select to PUBLIC tag visibility so ADMIN tags never leak", async () => {
            let capturedSelect!: {
                taggedShows: {
                    where: { tag: { visibility: string } };
                    select: { tag: { select: Record<string, boolean> } };
                };
            };
            mockFindMany.mockImplementation((args: unknown) => {
                capturedSelect = (args as { select: typeof capturedSelect })
                    .select;
                return Promise.resolve([]) as never;
            });

            await findShowsForHome({}, { date: "asc" });

            expect(capturedSelect.taggedShows.where).toEqual({
                tag: { visibility: "PUBLIC" },
            });
            expect(capturedSelect.taggedShows.select.tag.select).toEqual({
                slug: true,
                name: true,
            });
        });

        it("skips tags whose slug or name is null so the response only contains usable entries", async () => {
            const row = makeShowRow({
                taggedShows: [
                    { tag: { slug: "open mic", name: "Open Mic" } },
                    { tag: { slug: null, name: "No Slug" } },
                    { tag: { slug: "no-name", name: null } },
                ],
            });
            mockFindMany.mockResolvedValue([row] as never);

            const result = await findShowsForHome({}, { date: "asc" });

            expect(result[0].tags).toEqual([
                { slug: "open mic", name: "Open Mic" },
            ]);
        });
    });

    describe("skip + sortByHomeRelevance guard", () => {
        it("throws when skip>0 is combined with sortByHomeRelevance=true", async () => {
            await expect(
                findShowsForHome(
                    {},
                    { date: "asc" },
                    8,
                    { sortByHomeRelevance: true },
                    20,
                ),
            ).rejects.toThrow(/skip>0 is incompatible with sortByHomeRelevance/);
            expect(mockFindMany).not.toHaveBeenCalled();
        });

        it("allows skip>0 when sortByHomeRelevance is false or omitted", async () => {
            mockFindMany.mockResolvedValue([] as never);

            await findShowsForHome({}, { date: "asc" }, 8, {}, 20);

            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ skip: 20, take: 8 }),
            );
        });

        it("allows skip=0 when sortByHomeRelevance=true", async () => {
            mockFindMany.mockResolvedValue([] as never);

            await findShowsForHome(
                {},
                { date: "asc" },
                8,
                { sortByHomeRelevance: true },
                0,
            );

            expect(mockFindMany).toHaveBeenCalled();
        });
    });
});
