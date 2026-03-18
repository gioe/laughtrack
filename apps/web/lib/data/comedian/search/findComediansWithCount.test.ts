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
): QueryHelper {
    return {
        params: { sort, comedian, filters },
        getProfileId: () => profileId,
        getComedianNameClause: () => ({}),
        getComedianFiltersClause: () => ({}),
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
            expect(mockQueryRaw).not.toHaveBeenCalled();
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
            // Raw SQL returns IDs in ascending show-count order: 2, 1, 3
            mockQueryRaw.mockResolvedValue([
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

            expect(mockQueryRaw).toHaveBeenCalledOnce();
            expect(mockFindMany).toHaveBeenCalledOnce();
            // Result must be in SQL order: 2, 1, 3 (fewest first)
            expect(result.comedians.map((c) => c.id)).toEqual([2, 1, 3]);
        });

        it("returns comedians ordered by ascending show_count after re-sort", async () => {
            mockCount.mockResolvedValue(3);
            mockQueryRaw.mockResolvedValue([
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
            // Raw SQL returns IDs in sorted order: 3, 1, 2
            mockQueryRaw.mockResolvedValue([
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

            expect(mockQueryRaw).toHaveBeenCalledOnce();
            expect(mockFindMany).toHaveBeenCalledOnce();
            expect(result.totalCount).toBe(3);
            // Result must be in SQL order: 3, 1, 2
            expect(result.comedians.map((c) => c.id)).toEqual([3, 1, 2]);
        });

        it("returns comedians ordered by descending show_count after re-sort", async () => {
            mockCount.mockResolvedValue(3);
            mockQueryRaw.mockResolvedValue([
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
            mockQueryRaw.mockResolvedValue([] as never);

            const helper = makeHelper(SortParamValue.ShowCountDesc);
            const result = await findComediansWithCount(helper);

            expect(result.comedians).toEqual([]);
            expect(result.totalCount).toBe(0);
            expect(mockFindMany).not.toHaveBeenCalled();
        });

        it("does not use findMany without a take/skip limit (no fetch-all)", async () => {
            mockCount.mockResolvedValue(100);
            mockQueryRaw.mockResolvedValue([{ id: 1 }] as never);
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
});
