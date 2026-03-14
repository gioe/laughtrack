import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/db", () => ({
    db: { $transaction: vi.fn() },
}));
vi.mock("@/util/imageUtil", () => ({
    buildClubImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.png`,
    ),
}));
vi.mock("@/util/comedian/comedianUtil", () => ({
    filterAndMapLineupItems: vi.fn(() => []),
}));
vi.mock("@/util/ticket/ticketUtil", () => ({
    mapTickets: vi.fn((tickets: any[]) => tickets),
}));

import { findShowsWithCount } from "./findShowsWithCount";
import { db } from "@/lib/db";

const mockTransaction = vi.mocked(db.$transaction);

function makeHelper(
    overrides: Partial<{
        profileId: string | undefined;
        userId: string | undefined;
    }> = {},
) {
    return {
        getDateClause: vi.fn(() => ({})),
        getClubNameClause: vi.fn(() => ({})),
        getZipCodeClause: vi.fn(() => ({})),
        getLineupItemClause: vi.fn(() => ({ lineupItems: {} })),
        getShowTagsClause: vi.fn(() => ({})),
        getGenericClauses: vi.fn((count: number) => ({
            orderBy: [{ name: "asc" }],
            take: Math.min(10, count),
            skip: 0,
        })),
        getProfileId: vi.fn(() => overrides.profileId ?? undefined),
        getUserId: vi.fn(() => overrides.userId ?? undefined),
    };
}

function makeShow(
    overrides: Partial<{
        id: number;
        name: string;
        date: Date;
        description: string | null;
        popularity: number;
        tickets: any[];
        club: { name: string; address: string };
        lineupItems: any[];
    }> = {},
) {
    return {
        id: 1,
        name: "Test Show",
        date: new Date("2026-04-01"),
        description: null,
        popularity: 5,
        tickets: [],
        club: { name: "Test Club", address: "123 Main St" },
        lineupItems: [],
        ...overrides,
    };
}

function makeTx(countValue: number, findManyImpl?: (args: any) => any) {
    return {
        show: {
            count: vi.fn().mockResolvedValue(countValue),
            findMany: findManyImpl
                ? vi.fn().mockImplementation(findManyImpl)
                : vi.fn().mockResolvedValue([]),
        },
    };
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("findShowsWithCount", () => {
    describe("happy path", () => {
        it("returns totalCount and mapped shows from the transaction", async () => {
            const fakeShow = makeShow({ id: 42, name: "Friday Night Laughs" });

            mockTransaction.mockImplementation(async (fn: any) =>
                fn(makeTx(3, () => Promise.resolve([fakeShow]))),
            );

            const result = await findShowsWithCount(makeHelper() as any);

            expect(result.totalCount).toBe(3);
            expect(result.shows).toHaveLength(1);
            expect(result.shows[0].id).toBe(42);
            expect(result.shows[0].name).toBe("Friday Night Laughs");
        });

        it("returns empty shows array when count is 0", async () => {
            mockTransaction.mockImplementation(async (fn: any) =>
                fn(makeTx(0, () => Promise.resolve([]))),
            );

            const result = await findShowsWithCount(makeHelper() as any);

            expect(result.totalCount).toBe(0);
            expect(result.shows).toEqual([]);
        });

        it("maps club address and name onto the ShowDTO", async () => {
            const fakeShow = makeShow({
                club: { name: "Laugh Factory", address: "456 Sunset Blvd" },
            });

            mockTransaction.mockImplementation(async (fn: any) =>
                fn(makeTx(1, () => Promise.resolve([fakeShow]))),
            );

            const result = await findShowsWithCount(makeHelper() as any);

            expect(result.shows[0].clubName).toBe("Laugh Factory");
            expect(result.shows[0].address).toBe("456 Sunset Blvd");
        });
    });

    describe("pagination — getGenericClauses receives transaction-sourced count", () => {
        it("calls helper.getGenericClauses with the count from tx.show.count", async () => {
            const DB_COUNT = 47;

            mockTransaction.mockImplementation(async (fn: any) =>
                fn(makeTx(DB_COUNT)),
            );

            const helper = makeHelper() as any;
            await findShowsWithCount(helper);

            expect(helper.getGenericClauses).toHaveBeenCalledWith(DB_COUNT);
        });

        it("spreads the result of getGenericClauses into the findMany call", async () => {
            let capturedArgs: any;

            mockTransaction.mockImplementation(async (fn: any) =>
                fn(
                    makeTx(20, (args: any) => {
                        capturedArgs = args;
                        return Promise.resolve([]);
                    }),
                ),
            );

            const helper = makeHelper() as any;
            await findShowsWithCount(helper);

            // getGenericClauses returns { take: 10, skip: 0, orderBy: [...] }
            expect(capturedArgs.take).toBe(10);
            expect(capturedArgs.skip).toBe(0);
        });
    });

    describe("invocation contract — getClubNameClause and getZipCodeClause", () => {
        it("calls getClubNameClause and getZipCodeClause each twice when clauses have values", async () => {
            mockTransaction.mockImplementation(async (fn: any) =>
                fn(makeTx(3)),
            );

            const helper = {
                ...makeHelper(),
                getClubNameClause: vi.fn(() => ({
                    name: { equals: "Laugh Factory" },
                })),
                getZipCodeClause: vi.fn(() => ({
                    zipCode: { equals: "10001" },
                })),
            };

            await findShowsWithCount(helper as any);

            expect(helper.getClubNameClause).toHaveBeenCalledTimes(2);
            expect(helper.getZipCodeClause).toHaveBeenCalledTimes(2);
        });

        it("calls getClubNameClause and getZipCodeClause each once when clauses are empty", async () => {
            mockTransaction.mockImplementation(async (fn: any) =>
                fn(makeTx(0)),
            );

            const helper = makeHelper() as any;
            await findShowsWithCount(helper);

            expect(helper.getClubNameClause).toHaveBeenCalledTimes(1);
            expect(helper.getZipCodeClause).toHaveBeenCalledTimes(1);
        });
    });

    describe("error propagation", () => {
        it("propagates an Error thrown inside the transaction to the caller", async () => {
            const dbError = new Error("Transaction failed");

            mockTransaction.mockImplementation(async (fn: any) =>
                fn({
                    show: {
                        count: vi.fn().mockRejectedValue(dbError),
                        findMany: vi.fn(),
                    },
                }),
            );

            await expect(
                findShowsWithCount(makeHelper() as any),
            ).rejects.toThrow("Transaction failed");
        });

        it("replaces a non-Error rejection with a generic message", async () => {
            mockTransaction.mockRejectedValue("string error");

            await expect(
                findShowsWithCount(makeHelper() as any),
            ).rejects.toThrow("An unknown error occurred while fetching shows");
        });
    });

    describe("soldOut mapping", () => {
        it("sets soldOut to false when tickets array is empty", async () => {
            const show = makeShow({ tickets: [] });
            mockTransaction.mockImplementation(async (fn: any) =>
                fn(makeTx(1, () => Promise.resolve([show]))),
            );

            const result = await findShowsWithCount(makeHelper() as any);

            expect(result.shows[0].soldOut).toBe(false);
        });

        it("sets soldOut to true when all tickets are soldOut", async () => {
            const show = makeShow({
                tickets: [{ soldOut: true }, { soldOut: true }],
            });
            mockTransaction.mockImplementation(async (fn: any) =>
                fn(makeTx(1, () => Promise.resolve([show]))),
            );

            const result = await findShowsWithCount(makeHelper() as any);

            expect(result.shows[0].soldOut).toBe(true);
        });

        it("sets soldOut to false when tickets are partially sold out", async () => {
            const show = makeShow({
                tickets: [{ soldOut: true }, { soldOut: false }],
            });
            mockTransaction.mockImplementation(async (fn: any) =>
                fn(makeTx(1, () => Promise.resolve([show]))),
            );

            const result = await findShowsWithCount(makeHelper() as any);

            expect(result.shows[0].soldOut).toBe(false);
        });
    });

    describe("transaction options", () => {
        it("calls db.$transaction with RepeatableRead isolation level", async () => {
            mockTransaction.mockImplementation(async (fn: any) =>
                fn(makeTx(0)),
            );

            await findShowsWithCount(makeHelper() as any);

            expect(mockTransaction).toHaveBeenCalledWith(expect.any(Function), {
                isolationLevel: "RepeatableRead",
            });
        });
    });

    describe("favoriteComedians select", () => {
        it("includes favoriteComedians in the comedian select when profileId is set", async () => {
            let capturedSelect: any;

            mockTransaction.mockImplementation(async (fn: any) =>
                fn(
                    makeTx(1, (args: any) => {
                        capturedSelect = args.select;
                        return Promise.resolve([makeShow()]);
                    }),
                ),
            );

            const helper = makeHelper({ profileId: "profile-123" });
            await findShowsWithCount(helper as any);

            const comedianSelect =
                capturedSelect.lineupItems.select.comedian.select;
            expect(comedianSelect.favoriteComedians).toBeDefined();
            expect(comedianSelect.favoriteComedians.where.profileId).toBe(
                "profile-123",
            );
            expect(comedianSelect.favoriteComedians.select).toEqual({
                id: true,
            });
            expect(helper.getProfileId).toHaveBeenCalledTimes(2);
        });

        it("excludes favoriteComedians from the comedian select when profileId is not set", async () => {
            let capturedSelect: any;

            mockTransaction.mockImplementation(async (fn: any) =>
                fn(
                    makeTx(1, (args: any) => {
                        capturedSelect = args.select;
                        return Promise.resolve([makeShow()]);
                    }),
                ),
            );

            await findShowsWithCount(
                makeHelper({ profileId: undefined }) as any,
            );

            const comedianSelect =
                capturedSelect.lineupItems.select.comedian.select;
            expect(comedianSelect.favoriteComedians).toBeUndefined();
        });
    });
});
