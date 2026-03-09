import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/db", () => ({
    db: { $queryRaw: vi.fn() },
}));
vi.mock("@/util/imageUtil", () => ({
    buildComedianImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.png`,
    ),
}));

import { getTrendingComedians } from "./getTrendingComedians";
import { db } from "@/lib/db";

const mockQueryRaw = vi.mocked(db.$queryRaw);

function makeRow(
    overrides: Partial<{
        id: number;
        uuid: string;
        name: string;
        instagram_account: string | null;
        instagram_followers: number | null;
        tiktok_account: string | null;
        tiktok_followers: number | null;
        youtube_account: string | null;
        youtube_followers: number | null;
        website: string | null;
        popularity: number;
        linktree: string | null;
        show_count: number;
    }> = {},
) {
    return {
        id: 1,
        uuid: "uuid-1",
        name: "Alice Smith",
        instagram_account: "@alice",
        instagram_followers: 1000,
        tiktok_account: null,
        tiktok_followers: null,
        youtube_account: null,
        youtube_followers: null,
        website: "https://alice.example.com",
        popularity: 95,
        linktree: null,
        show_count: 5,
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("getTrendingComedians", () => {
    describe("mock setup — db.$queryRaw is injectable", () => {
        it("queries the DB when called with default args", async () => {
            mockQueryRaw.mockResolvedValue([]);
            await getTrendingComedians();
            expect(mockQueryRaw).toHaveBeenCalledOnce();
        });
    });

    describe("limit enforcement", () => {
        it("returns at most `limit` comedians when the pool is larger", async () => {
            const limit = 4;
            // pool = min(4 * 4, 50) = 16 rows returned by DB
            const rows = Array.from({ length: 16 }, (_, i) =>
                makeRow({
                    id: i + 1,
                    uuid: `uuid-${i + 1}`,
                    name: `Comedian ${i + 1}`,
                }),
            );
            mockQueryRaw.mockResolvedValue(rows);

            const result = await getTrendingComedians(limit, 0);

            expect(result.length).toBe(limit);
        });

        it("returns all rows when DB returns fewer than limit", async () => {
            const limit = 8;
            const rows = [makeRow({ id: 1, uuid: "uuid-1", name: "Only One" })];
            mockQueryRaw.mockResolvedValue(rows);

            const result = await getTrendingComedians(limit, 0);

            expect(result.length).toBe(1);
        });

        it("returns empty array when DB returns no rows", async () => {
            mockQueryRaw.mockResolvedValue([]);

            const result = await getTrendingComedians(8, 0);

            expect(result).toEqual([]);
        });

        it("returns exactly `limit` rows for paginated (offset > 0) requests", async () => {
            const limit = 5;
            const rows = Array.from({ length: 5 }, (_, i) =>
                makeRow({
                    id: i + 1,
                    uuid: `uuid-${i + 1}`,
                    name: `Page2 Comedian ${i + 1}`,
                }),
            );
            mockQueryRaw.mockResolvedValue(rows);

            const result = await getTrendingComedians(limit, 5);

            expect(result.length).toBe(limit);
        });
    });

    describe("show_count > 3 contract", () => {
        it("returns comedians whose show_count > 3 (SQL enforces this; mock simulates correct DB output)", async () => {
            const rows = [
                makeRow({
                    id: 1,
                    uuid: "uuid-1",
                    name: "Active A",
                    show_count: 4,
                }),
                makeRow({
                    id: 2,
                    uuid: "uuid-2",
                    name: "Active B",
                    show_count: 10,
                }),
                makeRow({
                    id: 3,
                    uuid: "uuid-3",
                    name: "Active C",
                    show_count: 7,
                }),
            ];
            mockQueryRaw.mockResolvedValue(rows);

            const result = await getTrendingComedians(8, 0);

            expect(result.every((c) => (c.show_count ?? 0) > 3)).toBe(true);
        });

        it("returns no comedians when DB returns no rows (show_count > 3 filter found no matches)", async () => {
            mockQueryRaw.mockResolvedValue([]);

            const result = await getTrendingComedians(8, 0);

            expect(result).toEqual([]);
        });

        it("surfaces show_count from each row so callers can verify the threshold", async () => {
            const rows = [
                makeRow({
                    id: 1,
                    uuid: "uuid-1",
                    name: "Comic A",
                    show_count: 5,
                }),
                makeRow({
                    id: 2,
                    uuid: "uuid-2",
                    name: "Comic B",
                    show_count: 12,
                }),
            ];
            mockQueryRaw.mockResolvedValue(rows);

            const result = await getTrendingComedians(8, 0);

            expect(result[0].show_count ?? 0).toBeGreaterThan(3);
            expect(result[1].show_count ?? 0).toBeGreaterThan(3);
        });
    });

    describe("row mapping", () => {
        it("maps a DB row to ComedianDTO correctly", async () => {
            const row = makeRow();
            mockQueryRaw.mockResolvedValue([row]);

            const result = await getTrendingComedians(8, 0);

            expect(result).toHaveLength(1);
            const dto = result[0];
            expect(dto.id).toBe(row.id);
            expect(dto.uuid).toBe(row.uuid);
            expect(dto.name).toBe(row.name);
            expect(dto.imageUrl).toBe(
                `https://cdn.example.com/${row.name}.png`,
            );
            expect(dto.show_count).toBe(row.show_count);
            expect(dto.social_data).toMatchObject({
                id: row.id,
                instagram_account: row.instagram_account,
                instagram_followers: row.instagram_followers,
                tiktok_account: row.tiktok_account,
                tiktok_followers: row.tiktok_followers,
                youtube_account: row.youtube_account,
                youtube_followers: row.youtube_followers,
                website: row.website,
                popularity: row.popularity,
                linktree: row.linktree,
            });
        });

        it("applies Number() cast to show_count from the DB row", async () => {
            const row = makeRow({ show_count: 7 });
            mockQueryRaw.mockResolvedValue([row]);

            const result = await getTrendingComedians(8, 0);

            expect(typeof result[0].show_count).toBe("number");
            expect(result[0].show_count).toBe(7);
        });

        it("handles null optional social fields", async () => {
            const row = makeRow({
                instagram_account: null,
                instagram_followers: null,
                tiktok_account: null,
                tiktok_followers: null,
                youtube_account: null,
                youtube_followers: null,
                website: null,
                linktree: null,
            });
            mockQueryRaw.mockResolvedValue([row]);

            const result = await getTrendingComedians(8, 0);
            const { social_data } = result[0];

            expect(social_data.instagram_account).toBeNull();
            expect(social_data.website).toBeNull();
        });
    });

    describe("shuffle behavior (offset = 0)", () => {
        it("returns a subset of pooled rows — all result IDs exist in the DB rows", async () => {
            const limit = 3;
            // pool = min(3 * 4, 50) = 12 rows
            const rows = Array.from({ length: 12 }, (_, i) =>
                makeRow({
                    id: i + 1,
                    uuid: `uuid-${i + 1}`,
                    name: `Comedian ${i + 1}`,
                }),
            );
            mockQueryRaw.mockResolvedValue(rows);

            const result = await getTrendingComedians(limit, 0);

            expect(result.length).toBe(limit);
            const inputIds = new Set(rows.map((r) => r.id));
            result.forEach((c) => expect(inputIds.has(c.id!)).toBe(true));
        });

        it("skips shuffle and fetches exact offset slice for paginated requests", async () => {
            const limit = 3;
            const rows = Array.from({ length: 3 }, (_, i) =>
                makeRow({
                    id: i + 10,
                    uuid: `uuid-${i + 10}`,
                    name: `Page2 ${i + 1}`,
                }),
            );
            mockQueryRaw.mockResolvedValue(rows);

            const result = await getTrendingComedians(limit, 3);

            // Paginated path: no shuffle, order preserved
            expect(result.map((c) => c.id)).toEqual([10, 11, 12]);
        });
    });
});
