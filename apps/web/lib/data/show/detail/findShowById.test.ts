import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/db", () => ({
    db: { show: { findUnique: vi.fn() } },
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
vi.mock("@/util/comedian/comedianUtil", () => ({
    filterAndMapLineupItems: vi.fn(() => []),
}));

import { findShowById } from "./findShowById";
import { db } from "@/lib/db";
import { NotFoundError } from "@/objects/NotFoundError";
import { mapTickets } from "@/util/ticket/ticketUtil";
import { filterAndMapLineupItems } from "@/util/comedian/comedianUtil";
import { Prisma } from "@prisma/client";

const mockFindUnique = vi.mocked(db.show.findUnique);
const mockMapTickets = vi.mocked(mapTickets);
const mockFilterAndMap = vi.mocked(filterAndMapLineupItems);

function makeShowRow(
    overrides: Partial<{
        id: number;
        name: string;
        date: Date;
        description: string | null;
        room: string | null;
        showPageUrl: string;
        tickets: any[];
        club: {
            id: number;
            name: string;
            address: string;
            hasImage: boolean;
            timezone: string | null;
            visible: boolean;
        };
        lineupItems: any[];
    }> = {},
) {
    return {
        id: 1,
        name: "Test Show",
        date: new Date("2026-06-01"),
        description: null,
        room: null,
        showPageUrl: "https://example.com/show/1",
        tickets: [],
        club: {
            id: 10,
            name: "Comedy Cellar",
            address: "117 Macdougal St",
            hasImage: true,
            timezone: "America/New_York",
            visible: true,
        },
        lineupItems: [],
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("findShowById", () => {
    describe("happy path", () => {
        it("returns mapped ShowDetailDTO and clubId", async () => {
            const row = makeShowRow({
                id: 42,
                name: "Friday Night Comedy",
                date: new Date("2026-07-04"),
                room: "Main Room",
                showPageUrl: "https://example.com/show/42",
                club: {
                    id: 99,
                    name: "Comedy Cellar",
                    address: "117 Macdougal St",
                    hasImage: true,
                    timezone: "America/New_York",
                    visible: true,
                },
            });
            mockFindUnique.mockResolvedValue(row as any);

            const result = await findShowById(42);

            expect(result.clubId).toBe(99);
            expect(result.show.id).toBe(42);
            expect(result.show.name).toBe("Friday Night Comedy");
            expect(result.show.clubName).toBe("Comedy Cellar");
            expect(result.show.address).toBe("117 Macdougal St");
            expect(result.show.room).toBe("Main Room");
            expect(result.show.showPageUrl).toBe("https://example.com/show/42");
            expect(result.show.timezone).toBe("America/New_York");
            expect(result.show.imageUrl).toBe(
                "https://cdn.example.com/Comedy Cellar.jpg",
            );
            expect(result.show.distanceMiles).toBeNull();
        });

        it("passes row.tickets to mapTickets and row.lineupItems to filterAndMapLineupItems", async () => {
            const tickets = [
                { price: 15, soldOut: false, purchaseUrl: null, type: "ga" },
            ];
            const lineupItems = [{ comedian: { id: 1, name: "Alice" } }];
            const row = makeShowRow({ tickets, lineupItems });
            mockFindUnique.mockResolvedValue(row as any);

            await findShowById(1);

            expect(mockMapTickets).toHaveBeenCalledWith(tickets);
            expect(mockFilterAndMap).toHaveBeenCalledWith(lineupItems);
        });

        it("propagates description when present", async () => {
            const row = makeShowRow({ description: "A great show" });
            mockFindUnique.mockResolvedValue(row as any);

            const result = await findShowById(1);

            expect(result.show.description).toBe("A great show");
        });

        it("maps null description to undefined", async () => {
            const row = makeShowRow({ description: null });
            mockFindUnique.mockResolvedValue(row as any);

            const result = await findShowById(1);

            expect(result.show.description).toBeUndefined();
        });

        it("computes soldOut=true when all tickets are soldOut", async () => {
            const row = makeShowRow({
                tickets: [
                    { price: 20, soldOut: true, purchaseUrl: null, type: "ga" },
                    {
                        price: 30,
                        soldOut: true,
                        purchaseUrl: null,
                        type: "vip",
                    },
                ],
            });
            mockFindUnique.mockResolvedValue(row as any);

            const result = await findShowById(1);

            expect(result.show.soldOut).toBe(true);
        });

        it("computes soldOut=false when at least one ticket is available", async () => {
            const row = makeShowRow({
                tickets: [
                    { price: 20, soldOut: true, purchaseUrl: null, type: "ga" },
                    {
                        price: 30,
                        soldOut: false,
                        purchaseUrl: "https://tix.example.com",
                        type: "vip",
                    },
                ],
            });
            mockFindUnique.mockResolvedValue(row as any);

            const result = await findShowById(1);

            expect(result.show.soldOut).toBe(false);
        });

        it("computes soldOut=false when there are no tickets", async () => {
            const row = makeShowRow({ tickets: [] });
            mockFindUnique.mockResolvedValue(row as any);

            const result = await findShowById(1);

            expect(result.show.soldOut).toBe(false);
        });
    });

    describe("NotFoundError", () => {
        it("throws NotFoundError when db.show.findUnique returns null", async () => {
            mockFindUnique.mockResolvedValue(null);

            await expect(findShowById(123)).rejects.toThrow(NotFoundError);
        });

        it("includes the show id in the not-found error message", async () => {
            mockFindUnique.mockResolvedValue(null);

            await expect(findShowById(456)).rejects.toThrow(/456/);
        });

        it("throws NotFoundError when the show exists but the club is not visible", async () => {
            const row = makeShowRow({
                id: 7,
                club: {
                    id: 10,
                    name: "Hidden Club",
                    address: "somewhere",
                    hasImage: false,
                    timezone: null,
                    visible: false,
                },
            });
            mockFindUnique.mockResolvedValue(row as any);

            await expect(findShowById(7)).rejects.toThrow(NotFoundError);
        });

        it("does not leak hidden-club data through the not-found message", async () => {
            const row = makeShowRow({
                id: 7,
                club: {
                    id: 10,
                    name: "Hidden Club",
                    address: "somewhere",
                    hasImage: false,
                    timezone: null,
                    visible: false,
                },
            });
            mockFindUnique.mockResolvedValue(row as any);

            await expect(findShowById(7)).rejects.toThrow(/7/);
            mockFindUnique.mockResolvedValue(row as any);
            await expect(findShowById(7)).rejects.not.toThrow(/Hidden Club/);
            mockFindUnique.mockResolvedValue(row as any);
            await expect(findShowById(7)).rejects.not.toThrow(/somewhere/);
        });
    });

    describe("Prisma error rewrapping", () => {
        it("rewraps PrismaClientKnownRequestError as a generic Error with 'Database error:' prefix", async () => {
            const prismaError = new Prisma.PrismaClientKnownRequestError(
                "Timed out",
                { code: "P2024", clientVersion: "6.5.0" },
            );
            mockFindUnique.mockRejectedValue(prismaError);

            await expect(findShowById(1)).rejects.toThrow(
                /^Database error: Timed out/,
            );
        });

        it("does not rewrap Prisma errors as NotFoundError", async () => {
            const prismaError = new Prisma.PrismaClientKnownRequestError(
                "boom",
                { code: "P2025", clientVersion: "6.5.0" },
            );
            mockFindUnique.mockRejectedValue(prismaError);

            await expect(findShowById(1)).rejects.not.toThrow(NotFoundError);
        });

        it("re-throws a generic Error unchanged (fallback branch)", async () => {
            const generic = new Error("boom");
            mockFindUnique.mockRejectedValue(generic);

            await expect(findShowById(1)).rejects.toBe(generic);
        });
    });
});
