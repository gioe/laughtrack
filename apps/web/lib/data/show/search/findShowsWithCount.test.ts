import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryHelper, SHOW_SORT_MAP } from "@/objects/class/query/QueryHelper";
import { SortParamValue } from "@/objects/enum/sortParamValue";

type FindManyArgs = {
    take?: number;
    skip?: number;
    select: {
        club: { select: { id?: boolean; timezone: boolean } };
        lineupItems: {
            select: {
                comedian: {
                    select: {
                        favoriteComedians?: {
                            where: { profileId: string };
                            select: { id: boolean };
                        };
                        _count?: unknown;
                        parentComedian: { select: { _count: unknown } };
                    };
                };
            };
        };
    };
};

const { mockCount, mockFindMany } = vi.hoisted(() => ({
    mockCount: vi.fn(),
    mockFindMany: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: { show: { count: mockCount, findMany: mockFindMany } },
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
    mapTickets: vi.fn((tickets: object[]) => tickets),
}));

import { findShowsWithCount } from "./findShowsWithCount";

function makeHelper(
    overrides: Partial<{
        profileId: string | undefined;
        userId: string | undefined;
        zip: string | undefined;
    }> = {},
) {
    return {
        params: { zip: overrides.zip ?? undefined },
        getDateClause: vi.fn(() => ({})),
        getClubNameClause: vi.fn(() => ({})),
        getZipCodeClause: vi.fn(() => ({})),
        getLineupItemClause: vi.fn(() => ({ lineupItems: {} })),
        getShowTagsClause: vi.fn(() => ({})),
        getFreeShowsClause: vi.fn(() => ({})),
        getGenericClauses: vi.fn((count: number) => ({
            orderBy: [{ name: "asc" }],
            take: Math.min(10, count),
            skip: 0,
        })),
        getProfileId: vi.fn(() => overrides.profileId ?? undefined),
        getUserId: vi.fn(() => overrides.userId ?? undefined),
        isZipCapTriggered: vi.fn(() => false),
    };
}

function makeShow(
    overrides: Partial<{
        id: number;
        name: string;
        date: Date;
        description: string | null;
        popularity: number;
        tickets: object[];
        club: {
            id?: number;
            name: string;
            address: string;
            zipCode?: string | null;
            hasImage?: boolean;
            timezone?: string | null;
        };
        lineupItems: object[];
    }> = {},
) {
    return {
        id: 1,
        name: "Test Show",
        date: new Date("2026-04-01"),
        description: null,
        popularity: 5,
        tickets: [],
        club: {
            id: 77,
            name: "Test Club",
            address: "123 Main St",
            zipCode: "10001",
            hasImage: true,
            timezone: "America/New_York",
        },
        lineupItems: [],
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
    mockFindMany.mockResolvedValue([]);
    mockCount.mockResolvedValue(0);
});

describe("findShowsWithCount", () => {
    describe("happy path", () => {
        it("returns totalCount and mapped shows", async () => {
            const fakeShow = makeShow({ id: 42, name: "Friday Night Laughs" });
            mockCount.mockResolvedValue(3);
            mockFindMany.mockResolvedValue([fakeShow]);

            const result = await findShowsWithCount(makeHelper() as never);

            expect(result.totalCount).toBe(3);
            expect(result.shows).toHaveLength(1);
            expect(result.shows[0].id).toBe(42);
            expect(result.shows[0].name).toBe("Friday Night Laughs");
        });

        it("returns empty shows array when count is 0", async () => {
            mockCount.mockResolvedValue(0);
            mockFindMany.mockResolvedValue([]);

            const result = await findShowsWithCount(makeHelper() as never);

            expect(result.totalCount).toBe(0);
            expect(result.shows).toEqual([]);
        });

        it("maps club id, address, and name onto the ShowDTO", async () => {
            const fakeShow = makeShow({
                club: {
                    id: 321,
                    name: "Laugh Factory",
                    address: "456 Sunset Blvd",
                },
            });
            mockCount.mockResolvedValue(1);
            mockFindMany.mockResolvedValue([fakeShow]);

            const result = await findShowsWithCount(makeHelper() as never);

            expect(result.shows[0].clubID).toBe(321);
            expect(result.shows[0].clubName).toBe("Laugh Factory");
            expect(result.shows[0].address).toBe("456 Sunset Blvd");
        });
    });

    describe("pagination — getGenericClauses receives count", () => {
        it("calls helper.getGenericClauses with the count from db.show.count", async () => {
            const DB_COUNT = 47;
            mockCount.mockResolvedValue(DB_COUNT);

            const helper = makeHelper();
            await findShowsWithCount(helper as never);

            expect(helper.getGenericClauses).toHaveBeenCalledWith(
                DB_COUNT,
                SHOW_SORT_MAP,
                [{ date: "asc" }, { id: "asc" }],
            );
        });

        it("spreads the result of getGenericClauses into the findMany call", async () => {
            mockCount.mockResolvedValue(20);
            let capturedArgs: Pick<FindManyArgs, "take" | "skip"> = {};
            mockFindMany.mockImplementation((args: unknown) => {
                capturedArgs = args as FindManyArgs;
                return Promise.resolve([]);
            });

            const helper = makeHelper();
            await findShowsWithCount(helper as never);

            // getGenericClauses returns { take: 10, skip: 0, orderBy: [...] }
            expect(capturedArgs.take).toBe(10);
            expect(capturedArgs.skip).toBe(0);
        });
    });

    describe("invocation contract — getClubNameClause and getZipCodeClause", () => {
        it("calls getClubNameClause and getZipCodeClause each once when clauses have values", async () => {
            mockCount.mockResolvedValue(3);

            const helper = {
                ...makeHelper(),
                getClubNameClause: vi.fn(() => ({
                    name: { equals: "Laugh Factory" },
                })),
                getZipCodeClause: vi.fn(() => ({
                    zipCode: { equals: "10001" },
                })),
            };

            await findShowsWithCount(helper as never);

            expect(helper.getClubNameClause).toHaveBeenCalledTimes(1);
            expect(helper.getZipCodeClause).toHaveBeenCalledTimes(1);
        });

        it("calls getClubNameClause and getZipCodeClause each once when clauses are empty", async () => {
            const helper = makeHelper();
            await findShowsWithCount(helper as never);

            expect(helper.getClubNameClause).toHaveBeenCalledTimes(1);
            expect(helper.getZipCodeClause).toHaveBeenCalledTimes(1);
        });
    });

    describe("error propagation", () => {
        it("propagates an Error thrown by db.show.count to the caller", async () => {
            const dbError = new Error("DB count failed");
            mockCount.mockRejectedValue(dbError);

            await expect(
                findShowsWithCount(makeHelper() as never),
            ).rejects.toThrow("DB count failed");
        });

        it("replaces a non-Error rejection with a generic message", async () => {
            mockCount.mockRejectedValue("string error");

            await expect(
                findShowsWithCount(makeHelper() as never),
            ).rejects.toThrow("An unknown error occurred while fetching shows");
        });

        it("propagates an Error thrown by db.show.findMany to the caller", async () => {
            const dbError = new Error("DB findMany failed");
            mockCount.mockResolvedValue(1);
            mockFindMany.mockRejectedValue(dbError);

            await expect(
                findShowsWithCount(makeHelper() as never),
            ).rejects.toThrow("DB findMany failed");
        });
    });

    describe("soldOut mapping", () => {
        it("sets soldOut to false when tickets array is empty", async () => {
            const show = makeShow({ tickets: [] });
            mockCount.mockResolvedValue(1);
            mockFindMany.mockResolvedValue([show]);

            const result = await findShowsWithCount(makeHelper() as never);

            expect(result.shows[0].soldOut).toBe(false);
        });

        it("sets soldOut to true when all tickets are soldOut", async () => {
            const show = makeShow({
                tickets: [{ soldOut: true }, { soldOut: true }],
            });
            mockCount.mockResolvedValue(1);
            mockFindMany.mockResolvedValue([show]);

            const result = await findShowsWithCount(makeHelper() as never);

            expect(result.shows[0].soldOut).toBe(true);
        });

        it("sets soldOut to false when tickets are partially sold out", async () => {
            const show = makeShow({
                tickets: [{ soldOut: true }, { soldOut: false }],
            });
            mockCount.mockResolvedValue(1);
            mockFindMany.mockResolvedValue([show]);

            const result = await findShowsWithCount(makeHelper() as never);

            expect(result.shows[0].soldOut).toBe(false);
        });
    });

    describe("favoriteComedians select", () => {
        it("includes favoriteComedians in the comedian select when profileId is set", async () => {
            let capturedSelect!: FindManyArgs["select"];
            mockCount.mockResolvedValue(1);
            mockFindMany.mockImplementation((args: unknown) => {
                capturedSelect = (args as FindManyArgs).select;
                return Promise.resolve([makeShow()]);
            });

            const helper = makeHelper({ profileId: "profile-123" });
            await findShowsWithCount(helper as never);

            const comedianSelect =
                capturedSelect.lineupItems.select.comedian.select;
            expect(comedianSelect.favoriteComedians).toBeDefined();
            expect(comedianSelect.favoriteComedians!.where.profileId).toBe(
                "profile-123",
            );
            expect(comedianSelect.favoriteComedians!.select).toEqual({
                id: true,
            });
            expect(helper.getProfileId).toHaveBeenCalledTimes(2);
        });

        it("selects comedian lineup counts for native featured-comedian rows", async () => {
            let capturedSelect!: FindManyArgs["select"];
            mockCount.mockResolvedValue(1);
            mockFindMany.mockImplementation((args: unknown) => {
                capturedSelect = (args as FindManyArgs).select;
                return Promise.resolve([makeShow()]);
            });

            await findShowsWithCount(makeHelper() as never);

            const comedianSelect =
                capturedSelect.lineupItems.select.comedian.select;
            expect(comedianSelect._count).toEqual({
                select: { lineupItems: true },
            });
            expect(comedianSelect.parentComedian.select._count).toEqual({
                select: { lineupItems: true },
            });
        });

        it("excludes favoriteComedians from the comedian select when profileId is not set", async () => {
            let capturedSelect!: FindManyArgs["select"];
            mockCount.mockResolvedValue(1);
            mockFindMany.mockImplementation((args: unknown) => {
                capturedSelect = (args as FindManyArgs).select;
                return Promise.resolve([makeShow()]);
            });

            await findShowsWithCount(
                makeHelper({ profileId: undefined }) as never,
            );

            const comedianSelect =
                capturedSelect.lineupItems.select.comedian.select;
            expect(comedianSelect.favoriteComedians).toBeUndefined();
        });
    });

    describe("timezone mapping", () => {
        it("selects club.timezone from the database", async () => {
            let capturedSelect!: FindManyArgs["select"];
            mockCount.mockResolvedValue(0);
            mockFindMany.mockImplementation((args: unknown) => {
                capturedSelect = (args as FindManyArgs).select;
                return Promise.resolve([]);
            });

            await findShowsWithCount(makeHelper() as never);

            expect(capturedSelect.club.select.timezone).toBe(true);
        });

        it("selects club.id from the database", async () => {
            let capturedSelect!: FindManyArgs["select"];
            mockCount.mockResolvedValue(0);
            mockFindMany.mockImplementation((args: unknown) => {
                capturedSelect = (args as FindManyArgs).select;
                return Promise.resolve([]);
            });

            await findShowsWithCount(makeHelper() as never);

            expect(capturedSelect.club.select.id).toBe(true);
        });

        it("maps a Los Angeles club.timezone onto the returned DTO", async () => {
            const show = makeShow({
                club: {
                    name: "Laugh Factory",
                    address: "8001 Sunset Blvd",
                    zipCode: "90046",
                    hasImage: true,
                    timezone: "America/Los_Angeles",
                },
            });
            mockCount.mockResolvedValue(1);
            mockFindMany.mockResolvedValue([show]);

            const result = await findShowsWithCount(makeHelper() as never);

            expect(result.shows[0].timezone).toBe("America/Los_Angeles");
        });

        it("maps a Chicago club.timezone onto the returned DTO", async () => {
            const show = makeShow({
                club: {
                    name: "The Laugh Factory Chicago",
                    address: "3175 N Broadway",
                    zipCode: "60657",
                    hasImage: true,
                    timezone: "America/Chicago",
                },
            });
            mockCount.mockResolvedValue(1);
            mockFindMany.mockResolvedValue([show]);

            const result = await findShowsWithCount(makeHelper() as never);

            expect(result.shows[0].timezone).toBe("America/Chicago");
        });

        it("maps a Denver club.timezone onto the returned DTO", async () => {
            const show = makeShow({
                club: {
                    name: "Comedy Works",
                    address: "1226 15th St",
                    zipCode: "80202",
                    hasImage: true,
                    timezone: "America/Denver",
                },
            });
            mockCount.mockResolvedValue(1);
            mockFindMany.mockResolvedValue([show]);

            const result = await findShowsWithCount(makeHelper() as never);

            expect(result.shows[0].timezone).toBe("America/Denver");
        });

        it("returns null timezone when the club has no timezone configured", async () => {
            const show = makeShow({
                club: {
                    name: "Unknown Venue",
                    address: "123 Main St",
                    zipCode: "00000",
                    hasImage: false,
                    timezone: null,
                },
            });
            mockCount.mockResolvedValue(1);
            mockFindMany.mockResolvedValue([show]);

            const result = await findShowsWithCount(makeHelper() as never);

            expect(result.shows[0].timezone).toBeNull();
        });
    });

    describe("price sort wiring (TASK-2140)", () => {
        // SHOW_SORT_MAP exposes PriceAsc/PriceDesc as minPrice-keyed sorts with
        // nulls:"last" both directions. Rationale for the null placement:
        // Show.minPrice is the cheapest *paid* ticket (the migration trigger
        // excludes price=0/NULL), so a NULL minPrice means "no priced tickets
        // attached." For "$$: Low to High" the user wants the cheapest paid
        // show on top, not a free RSVP show — Postgres's default ASC NULLS
        // LAST already does this. For "$$: High to Low" the Postgres default
        // is NULLS FIRST, which would lead the page with priceless rows; we
        // override to NULLS LAST so the highest paid show leads and the
        // no-price tail sits at the bottom regardless of direction. Free
        // shows surface via the Free filter (TASK-2141) instead.
        it("maps PriceAsc to minPrice asc with nulls:'last'", () => {
            expect(SHOW_SORT_MAP[SortParamValue.PriceAsc]).toEqual({
                field: "minPrice",
                direction: "asc",
                nulls: "last",
            });
        });

        it("maps PriceDesc to minPrice desc with nulls:'last'", () => {
            expect(SHOW_SORT_MAP[SortParamValue.PriceDesc]).toEqual({
                field: "minPrice",
                direction: "desc",
                nulls: "last",
            });
        });

        function buildHelper(sort: SortParamValue) {
            return new QueryHelper({
                params: { sort },
                timezone: "America/New_York",
            });
        }

        it("findShowsWithCount issues a minPrice asc NULLS LAST orderBy when sort=price_asc", async () => {
            let captured!: { orderBy: Record<string, unknown>[] };
            mockCount.mockResolvedValue(1);
            mockFindMany.mockImplementation((args: unknown) => {
                captured = args as { orderBy: Record<string, unknown>[] };
                return Promise.resolve([]);
            });

            await findShowsWithCount(buildHelper(SortParamValue.PriceAsc));

            expect(captured.orderBy[0]).toEqual({
                minPrice: { sort: "asc", nulls: "last" },
            });
            // Shows preserve their explicit date+id tiebreakers regardless of
            // primary sort, so multi-row ties resolve deterministically.
            expect(captured.orderBy.slice(1)).toEqual([
                { date: "asc" },
                { id: "asc" },
            ]);
        });

        it("findShowsWithCount issues a minPrice desc NULLS LAST orderBy when sort=price_desc", async () => {
            let captured!: { orderBy: Record<string, unknown>[] };
            mockCount.mockResolvedValue(1);
            mockFindMany.mockImplementation((args: unknown) => {
                captured = args as { orderBy: Record<string, unknown>[] };
                return Promise.resolve([]);
            });

            await findShowsWithCount(buildHelper(SortParamValue.PriceDesc));

            expect(captured.orderBy[0]).toEqual({
                minPrice: { sort: "desc", nulls: "last" },
            });
        });

        it("non-null-aware sort entries still use the compact orderBy shape", async () => {
            // Regression guard: extending SortEntry with optional nulls must
            // not change the orderBy shape for entries that omit it.
            let captured!: { orderBy: Record<string, unknown>[] };
            mockCount.mockResolvedValue(1);
            mockFindMany.mockImplementation((args: unknown) => {
                captured = args as { orderBy: Record<string, unknown>[] };
                return Promise.resolve([]);
            });

            await findShowsWithCount(buildHelper(SortParamValue.DateAsc));

            expect(captured.orderBy[0]).toEqual({ date: "asc" });
        });
    });

    describe("zipCapTriggered in ShowsResponse", () => {
        it("returns zipCapTriggered: true when helper.isZipCapTriggered() returns true", async () => {
            const helper = {
                ...makeHelper(),
                isZipCapTriggered: vi.fn(() => true),
            };

            const result = await findShowsWithCount(helper as never);

            expect(result.zipCapTriggered).toBe(true);
        });

        it("returns zipCapTriggered: false when helper.isZipCapTriggered() returns false", async () => {
            const result = await findShowsWithCount(makeHelper() as never);

            expect(result.zipCapTriggered).toBe(false);
        });
    });
});
