import { PGlite } from "@electric-sql/pglite";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/db", () => ({
    db: { $queryRaw: vi.fn() },
}));
vi.mock("@/util/imageUtil", () => ({
    buildComedianImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.png`,
    ),
}));

import {
    buildTrendingComediansQuery,
    getTrendingComedians,
} from "./getTrendingComedians";
import { db } from "@/lib/db";

const mockQueryRaw = vi.mocked(db.$queryRaw);
const FIXTURE_NOW = new Date("2026-07-01T00:00:00Z");

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
        has_image: boolean;
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
        has_image: true,
        show_count: 5,
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
});

type SqlLike = {
    strings: readonly string[];
    values: readonly unknown[];
};

function toPgliteQuery(query: SqlLike) {
    const values = query.values.map((value) =>
        value instanceof Date ? value.toISOString() : value,
    );
    const text = query.strings.reduce((sql, chunk, index) => {
        if (index >= values.length) {
            return sql + chunk;
        }
        return `${sql}${chunk}$${index + 1}`;
    }, "");
    return { text, values };
}

function firstQueryRawSql() {
    const query = mockQueryRaw.mock.calls[0]?.[0] as SqlLike;
    return {
        sql: query.strings.join("?"),
        values: query.values,
    };
}

const TRENDING_COMEDIANS_FIXTURE_SCHEMA = `
    CREATE TABLE comedians (
        id INTEGER PRIMARY KEY,
        uuid TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        instagram_account TEXT,
        instagram_followers INTEGER,
        tiktok_account TEXT,
        tiktok_followers INTEGER,
        youtube_account TEXT,
        youtube_followers INTEGER,
        website TEXT,
        popularity DOUBLE PRECISION NOT NULL DEFAULT 0,
        linktree TEXT,
        has_image BOOLEAN NOT NULL DEFAULT false,
        visible BOOLEAN NOT NULL DEFAULT true,
        parent_comedian_id INTEGER REFERENCES comedians(id)
    );

    CREATE TABLE clubs (
        id INTEGER PRIMARY KEY,
        zip_code TEXT
    );

    CREATE TABLE shows (
        id INTEGER PRIMARY KEY,
        date TIMESTAMPTZ NOT NULL,
        club_id INTEGER NOT NULL REFERENCES clubs(id)
    );

    CREATE TABLE lineup_items (
        show_id INTEGER NOT NULL REFERENCES shows(id),
        comedian_id TEXT NOT NULL REFERENCES comedians(uuid),
        PRIMARY KEY (show_id, comedian_id)
    );

    CREATE TABLE tags (
        id INTEGER PRIMARY KEY,
        slug TEXT
    );

    CREATE TABLE tagged_comedians (
        id INTEGER PRIMARY KEY,
        comedian_id TEXT NOT NULL REFERENCES comedians(uuid),
        tag_id INTEGER NOT NULL REFERENCES tags(id)
    );

    CREATE TABLE comedian_deny_list (
        name TEXT PRIMARY KEY
    );
`;

async function seedTrendingComediansFixture(db: PGlite) {
    await db.exec(TRENDING_COMEDIANS_FIXTURE_SCHEMA);
    await db.query(`
        INSERT INTO clubs (id, zip_code) VALUES
            (1, '10001'),
            (2, '94108')
    `);
    await db.query(`
        INSERT INTO comedians (
            id,
            uuid,
            name,
            popularity,
            has_image,
            visible,
            parent_comedian_id
        ) VALUES
            (1, 'alice', 'Alice Headliner', 0.90, true, true, NULL),
            (2, 'alice-alt', 'Alice Alias', 0.10, false, true, 1),
            (3, 'alice-hidden-alt', 'Alice Hidden Alias', 0.10, false, false, 1),
            (4, 'bob', 'Bob Regular', 0.80, false, true, NULL),
            (5, 'tagged', 'Tagged Alias Comic', 0.90, true, true, NULL),
            (6, 'denied', 'Denied Comic', 0.90, true, true, NULL),
            (7, 'low-popularity', 'Low Popularity Comic', 0.20, true, true, NULL),
            (8, 'no-shows', 'No Shows Comic', 0.90, true, true, NULL)
    `);
    await db.query("INSERT INTO tags (id, slug) VALUES (1, 'alias')");
    await db.query(
        "INSERT INTO tagged_comedians (id, comedian_id, tag_id) VALUES (1, 'tagged', 1)",
    );
    await db.query(
        "INSERT INTO comedian_deny_list (name) VALUES ('Denied Comic')",
    );

    const shows = [
        [101, "2026-08-01T00:00:00Z", 1],
        [102, "2026-08-02T00:00:00Z", 1],
        [103, "2026-08-03T00:00:00Z", 1],
        [104, "2026-08-04T00:00:00Z", 2],
        [105, "2026-08-05T00:00:00Z", 1],
        [106, "2026-06-01T00:00:00Z", 1],
        [201, "2026-08-01T00:00:00Z", 1],
        [202, "2026-08-02T00:00:00Z", 1],
        [203, "2026-08-03T00:00:00Z", 2],
        [204, "2026-08-04T00:00:00Z", 2],
        [301, "2026-08-01T00:00:00Z", 1],
        [302, "2026-08-02T00:00:00Z", 1],
        [303, "2026-08-03T00:00:00Z", 1],
        [304, "2026-08-04T00:00:00Z", 1],
        [401, "2026-08-01T00:00:00Z", 1],
        [402, "2026-08-02T00:00:00Z", 1],
        [403, "2026-08-03T00:00:00Z", 1],
        [404, "2026-08-04T00:00:00Z", 1],
        [501, "2026-08-01T00:00:00Z", 1],
        [502, "2026-08-02T00:00:00Z", 1],
        [503, "2026-08-03T00:00:00Z", 1],
        [504, "2026-08-04T00:00:00Z", 1],
    ] as const;

    for (const [id, date, clubId] of shows) {
        await db.query(
            "INSERT INTO shows (id, date, club_id) VALUES ($1, $2, $3)",
            [id, date, clubId],
        );
    }

    const lineupItems = [
        [101, "alice"],
        [102, "alice"],
        [103, "alice-alt"],
        [104, "alice-alt"],
        [105, "alice-hidden-alt"],
        [106, "alice"],
        [201, "bob"],
        [202, "bob"],
        [203, "bob"],
        [204, "bob"],
        [301, "tagged"],
        [302, "tagged"],
        [303, "tagged"],
        [304, "tagged"],
        [401, "denied"],
        [402, "denied"],
        [403, "denied"],
        [404, "denied"],
        [501, "low-popularity"],
        [502, "low-popularity"],
        [503, "low-popularity"],
        [504, "low-popularity"],
    ] as const;

    for (const [showId, comedianId] of lineupItems) {
        await db.query(
            "INSERT INTO lineup_items (show_id, comedian_id) VALUES ($1, $2)",
            [showId, comedianId],
        );
    }
}

function legacyTrendingComediansCountSql(zipCodes?: readonly string[]) {
    const zipJoin = zipCodes?.length
        ? "JOIN clubs cl ON cl.id = s.club_id"
        : "";
    const zipFilter = zipCodes?.length ? "AND cl.zip_code = ANY($4)" : "";
    const values = zipCodes?.length
        ? [FIXTURE_NOW.toISOString(), 0.4, 3, zipCodes]
        : [FIXTURE_NOW.toISOString(), 0.4, 3];
    return {
        text: `
            WITH comedian_counts AS (
                SELECT
                    c.id,
                    c.name,
                    c.has_image,
                    (
                        (
                            SELECT COUNT(*)
                            FROM lineup_items li
                            JOIN shows s ON s.id = li.show_id
                            ${zipJoin}
                            WHERE li.comedian_id = c.uuid
                              AND s.date > $1
                              ${zipFilter}
                        ) + COALESCE((
                            SELECT SUM(cnt) FROM (
                                SELECT COUNT(*) AS cnt
                                FROM comedians alt
                                JOIN lineup_items li ON li.comedian_id = alt.uuid
                                JOIN shows s ON s.id = li.show_id
                                ${zipJoin}
                                WHERE alt.parent_comedian_id = c.id
                                  AND alt.visible = true
                                  AND s.date > $1
                                  ${zipFilter}
                            ) t
                        ), 0)
                    )::int AS show_count
                FROM comedians c
                WHERE
                    c.visible = true
                    AND c.popularity > $2
                    AND c.parent_comedian_id IS NULL
                    AND NOT EXISTS (
                        SELECT 1 FROM tagged_comedians tc
                        JOIN tags t ON t.id = tc.tag_id
                        WHERE tc.comedian_id = c.uuid
                            AND t.slug IN ('alias', 'non_human', 'non comic')
                    )
                    AND NOT EXISTS (
                        SELECT 1 FROM comedian_deny_list dl
                        WHERE dl.name = c.name
                    )
                    AND (
                        EXISTS (
                            SELECT 1 FROM lineup_items li
                            JOIN shows s ON s.id = li.show_id
                            ${zipJoin}
                            WHERE li.comedian_id = c.uuid
                              AND s.date > $1
                              ${zipFilter}
                        ) OR EXISTS (
                            SELECT 1 FROM comedians alt
                            JOIN lineup_items li ON li.comedian_id = alt.uuid
                            JOIN shows s ON s.id = li.show_id
                            ${zipJoin}
                            WHERE alt.parent_comedian_id = c.id
                              AND alt.visible = true
                              AND s.date > $1
                              ${zipFilter}
                        )
                    )
            )
            SELECT id, name, show_count
            FROM comedian_counts
            WHERE show_count > $3
            ORDER BY has_image DESC, show_count DESC, name ASC
        `,
        values,
    };
}

async function trendingCountsFromQuery(
    db: PGlite,
    query: { text: string; values: unknown[] },
) {
    const result = await db.query<{
        id: number;
        name: string;
        show_count: number | bigint;
    }>(query.text, query.values);

    return result.rows.map((row) => ({
        id: Number(row.id),
        name: row.name,
        show_count: Number(row.show_count),
    }));
}

describe("getTrendingComedians", () => {
    describe("mock setup — db.$queryRaw is injectable", () => {
        it("queries the DB when called with default args", async () => {
            mockQueryRaw.mockResolvedValue([]);
            await getTrendingComedians();
            expect(mockQueryRaw).toHaveBeenCalledOnce();
        });
    });

    describe("zip-scoped crowd counts", () => {
        it("adds club zip filters when a zipCode option is provided", async () => {
            mockQueryRaw.mockResolvedValue([]);

            await getTrendingComedians(8, 0, {
                zipCode: "94108",
                distanceMiles: 25,
            });

            const { sql, values } = firstQueryRawSql();
            expect(sql).toContain("JOIN clubs cl ON cl.id = s.club_id");
            expect(sql).toContain("cl.zip_code IN");
            expect(values).toContain("94108");
        });

        it("does not add club zip filters for generic trending comedians", async () => {
            mockQueryRaw.mockResolvedValue([]);

            await getTrendingComedians();

            const { sql } = firstQueryRawSql();
            expect(sql).not.toContain("JOIN clubs cl ON cl.id = s.club_id");
            expect(sql).not.toContain("cl.zip_code IN");
        });
    });

    describe("popularity cutoff", () => {
        it("limits the candidate pool to comedians above 0.4 popularity", async () => {
            mockQueryRaw.mockResolvedValue([]);

            await getTrendingComedians();

            const { sql, values } = firstQueryRawSql();
            expect(sql).toContain("c.popularity >");
            expect(values).toContain(0.4);
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
        it("matches the legacy own-plus-visible-alias show_count query on fixture data", async () => {
            const fixtureDb = new PGlite();
            try {
                await seedTrendingComediansFixture(fixtureDb);

                for (const nearbyZips of [undefined, ["10001"]] as const) {
                    const legacyRows = await trendingCountsFromQuery(
                        fixtureDb,
                        legacyTrendingComediansCountSql(nearbyZips),
                    );
                    const groupedRows = await trendingCountsFromQuery(
                        fixtureDb,
                        toPgliteQuery(
                            buildTrendingComediansQuery({
                                now: FIXTURE_NOW,
                                fetchLimit: 50,
                                fetchOffset: 0,
                                nearbyZips,
                            }),
                        ),
                    );

                    expect(groupedRows).toEqual(legacyRows);
                }
            } finally {
                await fixtureDb.close();
            }
        });

        it("uses one grouped lineup join instead of correlated show-count subqueries", async () => {
            mockQueryRaw.mockResolvedValue([]);

            await getTrendingComedians();

            const query = mockQueryRaw.mock.calls[0]?.[0] as SqlLike;
            const sql = query.strings.join(" ");

            expect(sql).toContain("GROUP BY canonical_comedian_id");
            expect(sql).toContain("JOIN eligible_lineups el");
            expect(sql).not.toContain("SELECT COUNT(*)");
            expect(sql).not.toContain("SELECT SUM(cnt)");
        });

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

            expect(result.every((c) => c.showCount > 3)).toBe(true);
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

            expect(result[0].showCount).toBeGreaterThan(3);
            expect(result[1].showCount).toBeGreaterThan(3);
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
            expect(dto.showCount).toBe(row.show_count);
            expect(dto.socialData).toMatchObject({
                id: row.id,
                instagramAccount: row.instagram_account,
                instagramFollowers: row.instagram_followers,
                tiktokAccount: row.tiktok_account,
                tiktokFollowers: row.tiktok_followers,
                youtubeAccount: row.youtube_account,
                youtubeFollowers: row.youtube_followers,
                website: row.website,
                popularity: row.popularity,
                linktree: row.linktree,
            });
        });

        it("applies Number() cast to show_count from the DB row", async () => {
            const row = makeRow({ show_count: 7 });
            mockQueryRaw.mockResolvedValue([row]);

            const result = await getTrendingComedians(8, 0);

            expect(typeof result[0].showCount).toBe("number");
            expect(result[0].showCount).toBe(7);
        });

        it("coerces BigInt show_count from Postgres COUNT() to a JS number via Number()", async () => {
            // Postgres COUNT(*) returns BigInt in the Prisma $queryRaw result; Number() must
            // convert it to a plain JS number before it reaches the caller.
            const row = { ...makeRow(), show_count: BigInt(12) } as never;
            mockQueryRaw.mockResolvedValue([row]);

            const result = await getTrendingComedians(8, 0);

            expect(typeof result[0].showCount).toBe("number");
            expect(result[0].showCount).toBe(12);
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
            const { socialData } = result[0];

            expect(socialData.instagramAccount).toBeNull();
            expect(socialData.website).toBeNull();
        });
    });

    describe("error handling", () => {
        it("returns [] when the DB query throws", async () => {
            mockQueryRaw.mockRejectedValue(new Error("DB connection error"));

            const result = await getTrendingComedians(8, 0);

            expect(result).toEqual([]);
        });

        it("returns [] on error for paginated requests too", async () => {
            mockQueryRaw.mockRejectedValue(new Error("timeout"));

            const result = await getTrendingComedians(8, 10);

            expect(result).toEqual([]);
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

        it("does not regroup randomized first-page rows by image availability", async () => {
            const randomSpy = vi.spyOn(Math, "random").mockReturnValue(0.99);
            const rows = [
                ...Array.from({ length: 4 }, (_, i) =>
                    makeRow({
                        id: i + 1,
                        uuid: `fallback-${i + 1}`,
                        name: `Fallback ${i + 1}`,
                        has_image: false,
                    }),
                ),
                ...Array.from({ length: 8 }, (_, i) =>
                    makeRow({
                        id: i + 10,
                        uuid: `photo-${i + 1}`,
                        name: `Photo ${i + 1}`,
                        has_image: true,
                    }),
                ),
            ];
            mockQueryRaw.mockResolvedValue(rows);

            const result = await getTrendingComedians(8, 0);

            expect(result).toHaveLength(8);
            expect(result.map((comedian) => comedian.id)).toEqual([
                1, 2, 3, 4, 10, 11, 12, 13,
            ]);
            randomSpy.mockRestore();
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

    describe("hasImage propagation", () => {
        it("sets hasImage=true when the DB row's has_image is true", async () => {
            const row = makeRow({ id: 1, uuid: "uuid-1", name: "A" });
            row.has_image = true;
            mockQueryRaw.mockResolvedValue([row]);

            const [result] = await getTrendingComedians(1, 0);

            expect(result.hasImage).toBe(true);
        });

        it("sets hasImage=false when the DB row's has_image is false", async () => {
            const row = makeRow({ id: 1, uuid: "uuid-1", name: "A" });
            row.has_image = false;
            mockQueryRaw.mockResolvedValue([row]);

            const [result] = await getTrendingComedians(1, 0);

            expect(result.hasImage).toBe(false);
        });
    });
});
