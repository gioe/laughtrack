import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/db", () => ({
    db: {
        comedian: {
            count: vi.fn(),
            findMany: vi.fn(),
        },
        $queryRaw: vi.fn(),
    },
}));
vi.mock("@/util/imageUtil", () => ({
    buildComedianImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.png`,
    ),
}));

import { findComediansWithCount } from "./findComediansWithCount";
import { db } from "@/lib/db";
import {
    QueryHelper,
    COMEDIAN_SORT_MAP,
    COMEDIAN_SORT_MAP_ADMIN,
} from "@/objects/class/query/QueryHelper";
import { SortParamValue } from "@/objects/enum/sortParamValue";

const mockCount = vi.mocked(db.comedian.count);
const mockFindMany = vi.mocked(db.comedian.findMany);
const mockQueryRaw = vi.mocked(db.$queryRaw);

function makeHelper(
    sort: string = SortParamValue.PopularityDesc,
    comedian?: string,
    filters?: string,
    profileId?: string,
    isAdmin = false,
    extraParams: Record<string, unknown> = {},
): QueryHelper {
    return {
        params: { sort, comedian, filters, ...extraParams },
        isAdmin,
        getProfileId: () => profileId,
        getComedianNameClause: () => ({}),
        getComedianFiltersClause: () => ({}),
        // Mirrors the real method's "no fromDate → upcoming-only" default so
        // tests don't need to thread date params through every makeHelper call.
        getDateClause: () => ({ date: { gte: new Date().toISOString() } }),
        getZipCodeClause: () => ({}),
        getGenericClauses: (total: number) => ({
            orderBy: [{ popularity: "desc" as const }],
            take: Math.min(10, total),
            skip: 0,
        }),
    } as unknown as QueryHelper;
}

function makeComedianRow(id: number, showCount = 0, name = `Comedian ${id}`) {
    return {
        id,
        uuid: `uuid-${id}`,
        name,
        linktree: null,
        instagramAccount: null,
        instagramFollowers: null,
        tiktokAccount: null,
        tiktokFollowers: null,
        youtubeAccount: null,
        youtubeFollowers: null,
        website: null,
        popularity: 100,
        alternativeNames: [],
        taggedComedians: [],
        _count: { lineupItems: showCount },
        favoriteComedians: [],
    };
}

describe("findComediansWithCount", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        // Default: empty deny-list. Individual tests override for the show-count
        // raw-SQL path (which makes a second $queryRaw call for sorted IDs).
        mockQueryRaw.mockResolvedValue([] as never);
    });

    describe("regular sort (non show_count_desc)", () => {
        it("passes COMEDIAN_SORT_MAP as second arg to getGenericClauses", async () => {
            const DB_COUNT = 5;
            mockCount.mockResolvedValue(DB_COUNT);
            mockFindMany.mockResolvedValue([makeComedianRow(1)] as never);

            const capturedArgs: unknown[][] = [];
            const helper = makeHelper(SortParamValue.PopularityDesc);
            const originalFn = helper.getGenericClauses.bind(helper);
            helper.getGenericClauses = vi.fn((...args: unknown[]) => {
                capturedArgs.push(args);
                return originalFn(args[0] as number, args[1] as never);
            }) as unknown as typeof helper.getGenericClauses;

            await findComediansWithCount(helper);

            expect(capturedArgs.length).toBeGreaterThan(0);
            // Every call must forward COMEDIAN_SORT_MAP as the second argument
            for (const args of capturedArgs) {
                expect(args[1]).toBe(COMEDIAN_SORT_MAP);
            }
        });

        it("returns comedians via Prisma findMany with pagination", async () => {
            const rows = [makeComedianRow(1, 3), makeComedianRow(2, 1)];
            mockCount.mockResolvedValue(2);
            mockFindMany.mockResolvedValue(rows as never);

            const helper = makeHelper(SortParamValue.PopularityDesc);
            const result = await findComediansWithCount(helper);

            expect(result.totalCount).toBe(2);
            expect(result.comedians).toHaveLength(2);
            expect(mockFindMany).toHaveBeenCalledOnce();
            // $queryRaw is still called once — to fetch the deny list — but not for sorted IDs.
            expect(mockQueryRaw).toHaveBeenCalledOnce();
        });

        it("maps show_count from _count.lineupItems", async () => {
            mockCount.mockResolvedValue(1);
            mockFindMany.mockResolvedValue([makeComedianRow(1, 5)] as never);

            const result = await findComediansWithCount(makeHelper());

            expect(result.comedians[0].show_count).toBe(5);
        });
    });

    describe("show_count_asc sort", () => {
        it("uses $queryRaw for ordered IDs with ASC direction", async () => {
            mockCount.mockResolvedValue(3);
            // First $queryRaw call fetches the deny list (empty); second returns IDs.
            mockQueryRaw
                .mockResolvedValueOnce([] as never)
                .mockResolvedValueOnce([
                    { id: 2 },
                    { id: 1 },
                    { id: 3 },
                ] as never);
            mockFindMany.mockResolvedValue([
                makeComedianRow(1, 2),
                makeComedianRow(2, 1),
                makeComedianRow(3, 5),
            ] as never);

            const helper = makeHelper(SortParamValue.ShowCountAsc);
            const result = await findComediansWithCount(helper);

            expect(mockQueryRaw).toHaveBeenCalledTimes(2);
            expect(mockFindMany).toHaveBeenCalledOnce();
            // Result must be in SQL order: 2, 1, 3 (fewest first)
            expect(result.comedians.map((c) => c.id)).toEqual([2, 1, 3]);
        });

        it("returns comedians ordered by ascending show_count after re-sort", async () => {
            mockCount.mockResolvedValue(3);
            mockQueryRaw
                .mockResolvedValueOnce([] as never)
                .mockResolvedValueOnce([
                    { id: 2 },
                    { id: 1 },
                    { id: 3 },
                ] as never);
            mockFindMany.mockResolvedValue([
                makeComedianRow(1, 2),
                makeComedianRow(2, 1),
                makeComedianRow(3, 5),
            ] as never);

            const helper = makeHelper(SortParamValue.ShowCountAsc);
            const result = await findComediansWithCount(helper);

            expect(result.comedians[0].show_count).toBe(1);
            expect(result.comedians[1].show_count).toBe(2);
            expect(result.comedians[2].show_count).toBe(5);
        });
    });

    describe("show_count_desc sort", () => {
        it("uses $queryRaw for ordered IDs, then findMany by those IDs", async () => {
            mockCount.mockResolvedValue(3);
            // First call = deny list (empty); second = sorted IDs: 3, 1, 2
            mockQueryRaw
                .mockResolvedValueOnce([] as never)
                .mockResolvedValueOnce([
                    { id: 3 },
                    { id: 1 },
                    { id: 2 },
                ] as never);
            // findMany returns rows in arbitrary DB order
            mockFindMany.mockResolvedValue([
                makeComedianRow(1, 2),
                makeComedianRow(2, 1),
                makeComedianRow(3, 5),
            ] as never);

            const helper = makeHelper(SortParamValue.ShowCountDesc);
            const result = await findComediansWithCount(helper);

            expect(mockQueryRaw).toHaveBeenCalledTimes(2);
            expect(mockFindMany).toHaveBeenCalledOnce();
            expect(result.totalCount).toBe(3);
            // Result must be in SQL order: 3, 1, 2
            expect(result.comedians.map((c) => c.id)).toEqual([3, 1, 2]);
        });

        it("returns comedians ordered by descending show_count after re-sort", async () => {
            mockCount.mockResolvedValue(3);
            mockQueryRaw
                .mockResolvedValueOnce([] as never)
                .mockResolvedValueOnce([
                    { id: 3 },
                    { id: 1 },
                    { id: 2 },
                ] as never);
            mockFindMany.mockResolvedValue([
                makeComedianRow(1, 2),
                makeComedianRow(2, 1),
                makeComedianRow(3, 5),
            ] as never);

            const helper = makeHelper(SortParamValue.ShowCountDesc);
            const result = await findComediansWithCount(helper);

            expect(result.comedians[0].show_count).toBe(5);
            expect(result.comedians[1].show_count).toBe(2);
            expect(result.comedians[2].show_count).toBe(1);
        });

        it("returns empty array when raw query finds no IDs", async () => {
            mockCount.mockResolvedValue(0);
            mockQueryRaw
                .mockResolvedValueOnce([] as never)
                .mockResolvedValueOnce([] as never);

            const helper = makeHelper(SortParamValue.ShowCountDesc);
            const result = await findComediansWithCount(helper);

            expect(result.comedians).toEqual([]);
            expect(result.totalCount).toBe(0);
            expect(mockFindMany).not.toHaveBeenCalled();
        });

        it("includes the comedian_deny_list NOT EXISTS subquery in the raw-SQL branch", async () => {
            mockCount.mockResolvedValue(1);
            mockQueryRaw
                .mockResolvedValueOnce([] as never)
                .mockResolvedValueOnce([{ id: 1 }] as never);
            mockFindMany.mockResolvedValue([makeComedianRow(1, 3)] as never);

            const helper = makeHelper(SortParamValue.ShowCountDesc);
            await findComediansWithCount(helper);

            // The second $queryRaw call builds the sorted-IDs query; it must retain
            // the NOT EXISTS "comedian_deny_list" predicate so the show-count path
            // can't silently regress back to the original TASK-1547 bug.
            const secondCallArgs = mockQueryRaw.mock
                .calls[1]?.[0] as unknown as
                | { sql?: string; strings?: readonly string[] }
                | undefined;
            const sqlText =
                secondCallArgs?.sql ?? secondCallArgs?.strings?.join(" ") ?? "";
            expect(sqlText).toMatch(/comedian_deny_list/);
        });

        it("does not use findMany without a take/skip limit (no fetch-all)", async () => {
            mockCount.mockResolvedValue(100);
            mockQueryRaw
                .mockResolvedValueOnce([] as never)
                .mockResolvedValueOnce([{ id: 1 }] as never);
            mockFindMany.mockResolvedValue([makeComedianRow(1, 3)] as never);

            const helper = makeHelper(SortParamValue.ShowCountDesc);
            await findComediansWithCount(helper);

            // findMany called with `where: { id: { in: [...] } }` (page-only IDs)
            const call = mockFindMany.mock.calls[0]?.[0];
            expect(call?.where).toMatchObject({ id: { in: [1] } });
            // No orderBy or take/skip in the findMany call (ordering handled by raw SQL)
            expect(call).not.toHaveProperty("take");
            expect(call).not.toHaveProperty("skip");
        });
    });

    describe("admin sort gating", () => {
        it("passes COMEDIAN_SORT_MAP (not admin) to getGenericClauses for non-admin with InsertedAtDesc", async () => {
            mockCount.mockResolvedValue(1);
            mockFindMany.mockResolvedValue([makeComedianRow(1)] as never);

            const capturedMaps: unknown[] = [];
            const helper = makeHelper(
                SortParamValue.InsertedAtDesc,
                undefined,
                undefined,
                undefined,
                false,
            );
            const originalFn = helper.getGenericClauses.bind(helper);
            helper.getGenericClauses = vi.fn((...args: unknown[]) => {
                capturedMaps.push(args[1]);
                return originalFn(args[0] as number, args[1] as never);
            }) as unknown as typeof helper.getGenericClauses;

            await findComediansWithCount(helper);

            expect(capturedMaps[0]).toBe(COMEDIAN_SORT_MAP);
            expect(capturedMaps[0]).not.toBe(COMEDIAN_SORT_MAP_ADMIN);
        });

        it("passes COMEDIAN_SORT_MAP_ADMIN to getGenericClauses for admin with InsertedAtDesc", async () => {
            mockCount.mockResolvedValue(1);
            mockFindMany.mockResolvedValue([makeComedianRow(1)] as never);

            const capturedMaps: unknown[] = [];
            const helper = makeHelper(
                SortParamValue.InsertedAtDesc,
                undefined,
                undefined,
                undefined,
                true,
            );
            const originalFn = helper.getGenericClauses.bind(helper);
            helper.getGenericClauses = vi.fn((...args: unknown[]) => {
                capturedMaps.push(args[1]);
                return originalFn(args[0] as number, args[1] as never);
            }) as unknown as typeof helper.getGenericClauses;

            await findComediansWithCount(helper);

            expect(capturedMaps[0]).toBe(COMEDIAN_SORT_MAP_ADMIN);
        });
    });

    describe("deny-list filtering", () => {
        it("includes name:notIn clause on the Prisma findMany path when deny list is non-empty", async () => {
            mockCount.mockResolvedValue(5);
            mockQueryRaw.mockResolvedValueOnce([
                { name: "Fake Comedy Show" },
                { name: "90 Day Fiance: Sarper Guven" },
            ] as never);
            mockFindMany.mockResolvedValue([makeComedianRow(1)] as never);

            const helper = makeHelper(SortParamValue.PopularityDesc);
            await findComediansWithCount(helper);

            const call = mockFindMany.mock.calls[0]?.[0];
            expect(call?.where?.AND).toEqual(
                expect.arrayContaining([
                    expect.objectContaining({
                        name: {
                            notIn: [
                                "Fake Comedy Show",
                                "90 Day Fiance: Sarper Guven",
                            ],
                        },
                    }),
                ]),
            );
        });

        it("omits the notIn clause when the deny list is empty", async () => {
            mockCount.mockResolvedValue(2);
            mockQueryRaw.mockResolvedValueOnce([] as never);
            mockFindMany.mockResolvedValue([makeComedianRow(1)] as never);

            const helper = makeHelper(SortParamValue.PopularityDesc);
            await findComediansWithCount(helper);

            const call = mockFindMany.mock.calls[0]?.[0];
            const andArray = (call?.where?.AND ?? []) as Array<
                Record<string, unknown>
            >;
            const hasNotIn = andArray.some(
                (entry) => (entry.name as { notIn?: unknown })?.notIn,
            );
            expect(hasNotIn).toBe(false);
        });

        it("surfaces the error loudly when the deny-list query throws", async () => {
            mockCount.mockResolvedValue(1);
            mockQueryRaw.mockRejectedValueOnce(
                new Error("comedian_deny_list does not exist"),
            );
            mockFindMany.mockResolvedValue([makeComedianRow(1)] as never);

            const helper = makeHelper(SortParamValue.PopularityDesc);
            // A silent fallback would re-expose the false positives this filter
            // is meant to hide, so findComediansWithCount must throw instead.
            await expect(findComediansWithCount(helper)).rejects.toThrow(
                /Failed to fetch comedians/,
            );
        });

        it("passes the denied names into the count query whereClause", async () => {
            mockQueryRaw.mockResolvedValueOnce([
                { name: "Blocked Name" },
            ] as never);
            mockCount.mockResolvedValue(0);
            mockFindMany.mockResolvedValue([] as never);

            const helper = makeHelper(SortParamValue.PopularityDesc);
            await findComediansWithCount(helper);

            const countCall = mockCount.mock.calls[0]?.[0];
            const andArray = (countCall?.where?.AND ?? []) as Array<
                Record<string, unknown>
            >;
            expect(andArray).toEqual(
                expect.arrayContaining([
                    expect.objectContaining({
                        name: { notIn: ["Blocked Name"] },
                    }),
                ]),
            );
        });
    });

    describe("hasImage propagation", () => {
        it("sets hasImage=true when the row has hasImage=true and false otherwise", async () => {
            const withImage: any = makeComedianRow(1);
            withImage.hasImage = true;
            const withoutImage: any = makeComedianRow(2);
            withoutImage.hasImage = false;
            mockCount.mockResolvedValue(2);
            mockFindMany.mockResolvedValue([withImage, withoutImage] as never);

            const { comedians } = await findComediansWithCount(makeHelper());

            expect(comedians.map((c) => c.hasImage)).toEqual([true, false]);
        });
    });

    describe("advanced comedian filters (zip / date / minUpcomingShows)", () => {
        it("resolves matching uuids via raw SQL and applies uuid IN clause when minUpcomingShows > 0", async () => {
            mockCount.mockResolvedValue(1);
            // 1st $queryRaw = deny list (empty); 2nd = matching uuids for the filter.
            mockQueryRaw
                .mockResolvedValueOnce([] as never)
                .mockResolvedValueOnce([
                    { uuid: "uuid-1" },
                    { uuid: "uuid-2" },
                ] as never);
            mockFindMany.mockResolvedValue([makeComedianRow(1)] as never);

            const helper = makeHelper(
                SortParamValue.PopularityDesc,
                undefined,
                undefined,
                undefined,
                false,
                { minUpcomingShows: "5" },
            );
            await findComediansWithCount(helper);

            // The 2nd $queryRaw call is the upcoming-shows subquery — threshold flows via .values.
            const filterCall = mockQueryRaw.mock.calls[1]?.[0] as {
                strings: string[];
                values: unknown[];
            };
            const sql = filterCall.strings.join(" ");
            expect(sql).toContain('FROM "lineup_items"');
            // Default helper applies the upcoming-only bound (showFilter.date = NOW)
            // so the scoped form uses s.date >= <Date> rather than the bare fallback.
            expect(sql).toContain("s.date >=");
            expect(filterCall.values).toContain(5);

            const call = mockFindMany.mock.calls[0]?.[0];
            expect(call?.where?.uuid).toEqual({ in: ["uuid-1", "uuid-2"] });
            // totalShows is no longer part of the filter — guard against regression.
            expect(call?.where?.totalShows).toBeUndefined();
        });

        it("short-circuits to empty result when no comedians meet minUpcomingShows", async () => {
            mockCount.mockResolvedValue(99);
            mockQueryRaw
                .mockResolvedValueOnce([] as never) // deny list
                .mockResolvedValueOnce([] as never); // no matches
            mockFindMany.mockResolvedValue([] as never);

            const helper = makeHelper(
                SortParamValue.PopularityDesc,
                undefined,
                undefined,
                undefined,
                false,
                { minUpcomingShows: "20" },
            );
            const result = await findComediansWithCount(helper);

            expect(result).toEqual({ comedians: [], totalCount: 0 });
            // findMany must not be called when the pre-fetch returned zero uuids.
            expect(mockFindMany).not.toHaveBeenCalled();
        });

        it("omits uuid filter and skips pre-fetch when minUpcomingShows is missing or zero", async () => {
            mockCount.mockResolvedValue(1);
            mockFindMany.mockResolvedValue([makeComedianRow(1)] as never);

            await findComediansWithCount(makeHelper());

            const call = mockFindMany.mock.calls[0]?.[0];
            expect(call?.where?.uuid).toBeUndefined();
            // Only one $queryRaw call: the deny-list fetch. No upcoming-shows pre-fetch.
            expect(mockQueryRaw).toHaveBeenCalledTimes(1);
        });

        it("nests the zip-code clause under lineupItems.some.show.club when zip is set", async () => {
            mockCount.mockResolvedValue(1);
            mockFindMany.mockResolvedValue([makeComedianRow(1)] as never);

            const helper = makeHelper(
                SortParamValue.PopularityDesc,
                undefined,
                undefined,
                undefined,
                false,
                { zip: "10001" },
            );
            // Override the default empty zip clause to return a real Prisma shape.
            (
                helper as unknown as { getZipCodeClause: () => unknown }
            ).getZipCodeClause = () => ({
                zipCode: { in: ["10001", "10002"] },
            });

            await findComediansWithCount(helper);

            const call = mockFindMany.mock.calls[0]?.[0];
            const showClause = call?.where?.lineupItems?.some?.show as
                | { club?: { zipCode?: unknown } }
                | undefined;
            expect(showClause?.club?.zipCode).toEqual({
                in: ["10001", "10002"],
            });
        });

        it("propagates the date clause from getDateClause into lineupItems.some.show", async () => {
            mockCount.mockResolvedValue(1);
            mockFindMany.mockResolvedValue([makeComedianRow(1)] as never);

            const helper = makeHelper(
                SortParamValue.PopularityDesc,
                undefined,
                undefined,
                undefined,
                false,
                { fromDate: "2026-05-01", toDate: "2026-05-31" },
            );
            (
                helper as unknown as { getDateClause: () => unknown }
            ).getDateClause = () => ({
                date: {
                    gte: "2026-05-01T00:00:00Z",
                    lte: "2026-05-31T23:59:59Z",
                },
            });

            await findComediansWithCount(helper);

            const call = mockFindMany.mock.calls[0]?.[0];
            const showClause = call?.where?.lineupItems?.some?.show as
                | { date?: { gte?: string; lte?: string } }
                | undefined;
            expect(showClause?.date?.gte).toBe("2026-05-01T00:00:00Z");
            expect(showClause?.date?.lte).toBe("2026-05-31T23:59:59Z");
        });

        it("includes an upcoming-shows COUNT subquery in the raw-SQL where conditions when minUpcomingShows is set on a show_count sort (and skips the Prisma-path pre-fetch)", async () => {
            mockCount.mockResolvedValue(1);
            // Call order: deny list → sorted IDs. The pre-fetch is skipped on
            // the show_count sort path since the raw-SQL branch applies the
            // same threshold directly.
            mockQueryRaw
                .mockResolvedValueOnce([] as never) // deny list
                .mockResolvedValueOnce([{ id: 1 }] as never); // sorted IDs
            mockFindMany.mockResolvedValue([makeComedianRow(1, 3)] as never);

            const helper = makeHelper(
                SortParamValue.ShowCountDesc,
                undefined,
                undefined,
                undefined,
                false,
                { minUpcomingShows: "10" },
            );
            await findComediansWithCount(helper);

            // Only 2 raw calls — no pre-fetch round-trip.
            expect(mockQueryRaw).toHaveBeenCalledTimes(2);

            // The 2nd $queryRaw call is the sorted-ID query — the count subquery
            // filters on future-dated shows and the threshold flows via .values.
            const sortedCall = mockQueryRaw.mock.calls[1]?.[0] as {
                strings: string[];
                values: unknown[];
            };
            const sql = sortedCall.strings.join(" ");
            expect(sql).toContain('FROM "lineup_items"');
            // Default helper applies the upcoming-only bound (showFilter.date = NOW)
            // so the scoped form uses s.date >= <Date> rather than the bare fallback.
            expect(sql).toContain("s.date >=");
            // Guard against regression: old implementation filtered on c."total_shows".
            expect(sql).not.toContain('c."total_shows" >=');
            expect(sortedCall.values).toContain(10);
        });

        it("scopes the pre-fetch subquery to the user's zip + date filters on the Prisma path", async () => {
            mockCount.mockResolvedValue(1);
            mockQueryRaw
                .mockResolvedValueOnce([] as never) // deny list
                .mockResolvedValueOnce([{ uuid: "uuid-1" }] as never); // pre-fetch
            mockFindMany.mockResolvedValue([makeComedianRow(1)] as never);

            const helper = makeHelper(
                SortParamValue.PopularityDesc,
                undefined,
                undefined,
                undefined,
                false,
                {
                    minUpcomingShows: "3",
                    zip: "10001",
                    fromDate: "2026-05-01",
                    toDate: "2026-05-31",
                },
            );
            (
                helper as unknown as { getZipCodeClause: () => unknown }
            ).getZipCodeClause = () => ({
                zipCode: { in: ["10001", "10002"] },
            });
            (
                helper as unknown as { getDateClause: () => unknown }
            ).getDateClause = () => ({
                date: {
                    gte: "2026-05-01T00:00:00Z",
                    lte: "2026-05-31T23:59:59Z",
                },
            });

            await findComediansWithCount(helper);

            // 2nd $queryRaw is the pre-fetch; its SQL must include the zip
            // JOIN/IN clause and the date bounds — not a bare `s.date > NOW()`.
            const prefetchCall = mockQueryRaw.mock.calls[1]?.[0] as {
                strings: string[];
                values: unknown[];
            };
            const sql = prefetchCall.strings.join(" ");
            expect(sql).toContain('JOIN "clubs" cl ON s."club_id" = cl.id');
            expect(sql).toContain('cl."zip_code" IN');
            // Zips and the date bounds are parameterized, so they flow via .values.
            expect(prefetchCall.values).toEqual(
                expect.arrayContaining(["10001", "10002", 3]),
            );
            expect(
                prefetchCall.values.some(
                    (v) =>
                        v instanceof Date &&
                        v.toISOString().startsWith("2026-05-01"),
                ),
            ).toBe(true);
            expect(
                prefetchCall.values.some(
                    (v) =>
                        v instanceof Date &&
                        v.toISOString().startsWith("2026-05-31"),
                ),
            ).toBe(true);
            // Bare "> NOW()" fallback is only used when no explicit bounds exist;
            // here the user-supplied bounds take over.
            expect(sql).not.toContain("s.date > NOW()");
        });

        it("threads zip + date predicates into both the EXISTS lineup check and the ORDER BY count subquery on the raw-SQL show_count branch", async () => {
            mockCount.mockResolvedValue(1);
            mockQueryRaw
                .mockResolvedValueOnce([] as never) // deny list
                .mockResolvedValueOnce([{ id: 1 }] as never); // sorted IDs
            mockFindMany.mockResolvedValue([makeComedianRow(1, 3)] as never);

            const helper = makeHelper(
                SortParamValue.ShowCountDesc,
                undefined,
                undefined,
                undefined,
                false,
                {
                    zip: "10001",
                    fromDate: "2026-05-01",
                    toDate: "2026-05-31",
                },
            );
            // Real Prisma shapes for the predicates the raw-SQL branch unpacks.
            (
                helper as unknown as { getZipCodeClause: () => unknown }
            ).getZipCodeClause = () => ({
                zipCode: { in: ["10001", "10002"] },
            });
            (
                helper as unknown as { getDateClause: () => unknown }
            ).getDateClause = () => ({
                date: {
                    gte: "2026-05-01T00:00:00Z",
                    lte: "2026-05-31T23:59:59Z",
                },
            });

            await findComediansWithCount(helper);

            const sortedCall = mockQueryRaw.mock.calls[1]?.[0] as {
                strings: string[];
                values: unknown[];
            };
            const sql = sortedCall.strings.join(" ");
            // Zip subquery joins clubs and IN-filters by zip_code; both the EXISTS
            // and ORDER BY count subqueries reference cl."zip_code".
            expect(sql).toContain('cl."zip_code"');
            expect(sql).toContain('JOIN "clubs" cl ON s."club_id" = cl.id');
            // The resolved zip strings flow through .values as parameters.
            expect(sortedCall.values).toEqual(
                expect.arrayContaining(["10001", "10002"]),
            );
            // Date bounds also flow through .values as Date objects.
            const hasDateValue = sortedCall.values.some(
                (v) =>
                    v instanceof Date &&
                    v.toISOString().startsWith("2026-05-01"),
            );
            expect(hasDateValue).toBe(true);
        });
    });
});
