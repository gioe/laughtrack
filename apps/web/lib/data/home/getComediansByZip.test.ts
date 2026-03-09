import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/db", () => ({
    db: { $queryRaw: vi.fn() },
}));
vi.mock("@/util/imageUtil", () => ({
    buildComedianImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.png`,
    ),
}));

import { getComediansByZip } from "./getComediansByZip";
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
        show_count: 3,
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("getComediansByZip", () => {
    describe("early-return guards", () => {
        it("returns [] immediately for empty string without querying the DB", async () => {
            const result = await getComediansByZip("");
            expect(result).toEqual([]);
            expect(mockQueryRaw).not.toHaveBeenCalled();
        });

        it("returns [] immediately for invalid zip (non-digits)", async () => {
            const result = await getComediansByZip("abcde");
            expect(result).toEqual([]);
            expect(mockQueryRaw).not.toHaveBeenCalled();
        });

        it("returns [] immediately for too-short zip", async () => {
            const result = await getComediansByZip("1234");
            expect(result).toEqual([]);
            expect(mockQueryRaw).not.toHaveBeenCalled();
        });

        it("returns [] immediately for too-long zip without hyphen", async () => {
            const result = await getComediansByZip("123456");
            expect(result).toEqual([]);
            expect(mockQueryRaw).not.toHaveBeenCalled();
        });

        it("returns [] immediately for a zip with wrong separator", async () => {
            const result = await getComediansByZip("10001_1234");
            expect(result).toEqual([]);
            expect(mockQueryRaw).not.toHaveBeenCalled();
        });
    });

    describe("valid zip formats", () => {
        it("accepts a standard 5-digit zip and queries the DB", async () => {
            mockQueryRaw.mockResolvedValue([]);
            await getComediansByZip("10001");
            expect(mockQueryRaw).toHaveBeenCalledOnce();
        });

        it("accepts ZIP+4 format and queries the DB", async () => {
            mockQueryRaw.mockResolvedValue([]);
            await getComediansByZip("10001-1234");
            expect(mockQueryRaw).toHaveBeenCalledOnce();
        });
    });

    describe("happy path — row mapping", () => {
        it("maps a single DB row to a ComedianDTO correctly", async () => {
            const row = makeRow();
            mockQueryRaw.mockResolvedValue([row]);

            const result = await getComediansByZip("10001");

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

        it("coerces show_count to a JS number", async () => {
            // Prisma raw queries return BigInt for COUNT; the function casts with Number()
            const row = makeRow({ show_count: BigInt(5) as unknown as number });
            mockQueryRaw.mockResolvedValue([row]);

            const result = await getComediansByZip("10001");
            expect(typeof result[0].show_count).toBe("number");
            expect(result[0].show_count).toBe(5);
        });

        it("returns an empty array when the DB returns no rows", async () => {
            mockQueryRaw.mockResolvedValue([]);
            const result = await getComediansByZip("10001");
            expect(result).toEqual([]);
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

            const result = await getComediansByZip("10001");
            const { social_data } = result[0];
            expect(social_data.instagram_account).toBeNull();
            expect(social_data.website).toBeNull();
        });
    });

    describe("ordering and limit", () => {
        it("preserves the row order returned by the DB (popularity DESC is enforced by SQL)", async () => {
            const rows = [
                makeRow({
                    id: 10,
                    uuid: "uuid-10",
                    name: "Top Comedian",
                    popularity: 100,
                }),
                makeRow({
                    id: 20,
                    uuid: "uuid-20",
                    name: "Mid Comedian",
                    popularity: 50,
                }),
                makeRow({
                    id: 30,
                    uuid: "uuid-30",
                    name: "Low Comedian",
                    popularity: 10,
                }),
            ];
            mockQueryRaw.mockResolvedValue(rows);

            const result = await getComediansByZip("10001");

            expect(result.map((c) => c.id)).toEqual([10, 20, 30]);
        });

        it("returns at most 8 results (LIMIT is enforced by SQL; function maps whatever DB returns)", async () => {
            const rows = Array.from({ length: 8 }, (_, i) =>
                makeRow({
                    id: i + 1,
                    uuid: `uuid-${i + 1}`,
                    name: `Comedian ${i + 1}`,
                    popularity: 100 - i,
                }),
            );
            mockQueryRaw.mockResolvedValue(rows);

            const result = await getComediansByZip("10001");
            expect(result).toHaveLength(8);
        });
    });

    describe("tag exclusion and alias filtering", () => {
        it("does not include rows with excluded tags when DB enforces the filter (rows absent from results)", async () => {
            // The SQL excludes comedians tagged alias/non_human/non_comic via NOT EXISTS.
            // In unit tests we verify the DB is called and rows are mapped as-is —
            // the absence of such comedians is controlled by the SQL query.
            const legitRow = makeRow({
                id: 1,
                uuid: "uuid-1",
                name: "Clean Comic",
            });
            mockQueryRaw.mockResolvedValue([legitRow]);

            const result = await getComediansByZip("10001");
            expect(result).toHaveLength(1);
            expect(result[0].name).toBe("Clean Comic");
        });

        it("excludes alias comedians — parent_comedian_id IS NULL enforced in SQL", async () => {
            // Only non-alias (parentComedianId IS NULL) rows reach the function;
            // confirm mapping handles them without error.
            const rows = [
                makeRow({ id: 1, uuid: "uuid-1", name: "Headliner A" }),
                makeRow({ id: 2, uuid: "uuid-2", name: "Headliner B" }),
            ];
            mockQueryRaw.mockResolvedValue(rows);

            const result = await getComediansByZip("10001");
            expect(result.map((c) => c.name)).toEqual([
                "Headliner A",
                "Headliner B",
            ]);
        });
    });
});
