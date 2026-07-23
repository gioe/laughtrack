import { PGlite } from "@electric-sql/pglite";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
    afterAll,
    beforeAll,
    beforeEach,
    describe,
    expect,
    it,
    vi,
} from "vitest";

vi.mock("@/lib/db", () => ({
    db: { $queryRaw: vi.fn() },
}));

import {
    buildFavoriteGrowthQuery,
    getFavoriteGrowth,
    getFavoriteGrowthWindows,
} from "./favoriteGrowth";
import { db } from "@/lib/db";

const mockQueryRaw = vi.mocked(db.$queryRaw);
const AS_OF = new Date("2026-07-23T15:30:00Z");
const MIGRATION_SQL = readFileSync(
    resolve(
        process.cwd(),
        "prisma/migrations/20260723120000_add_favorite_comedian_created_at/migration.sql",
    ),
    "utf8",
);

type SqlLike = {
    strings: readonly string[];
    values: readonly unknown[];
};

function toPgliteQuery(query: SqlLike) {
    const values = query.values.map((value) =>
        value instanceof Date ? value.toISOString() : value,
    );
    const text = query.strings.reduce((sql, chunk, index) => {
        if (index >= values.length) return sql + chunk;
        return `${sql}${chunk}$${index + 1}`;
    }, "");
    return { text, values };
}

async function runAggregate(fixtureDb: PGlite) {
    const query = toPgliteQuery(buildFavoriteGrowthQuery(AS_OF));
    const result = await fixtureDb.query<{
        comedian_id: string;
        recent_count: bigint | number;
        baseline_count: bigint | number;
    }>(query.text, query.values);

    return result.rows.map((row) => ({
        comedianId: row.comedian_id,
        recentCount: Number(row.recent_count),
        baselineCount: Number(row.baseline_count),
    }));
}

describe("favorite growth migration", () => {
    it("leaves legacy timestamps unknown and timestamps only future rows", async () => {
        const fixtureDb = new PGlite();
        try {
            await fixtureDb.exec(`
                CREATE TABLE favorite_comedians (
                    profile_id TEXT NOT NULL,
                    comedian_id TEXT NOT NULL,
                    PRIMARY KEY (profile_id, comedian_id)
                );
                INSERT INTO favorite_comedians (profile_id, comedian_id)
                VALUES ('legacy-profile', 'legacy-comedian');
            `);
            await fixtureDb.exec(MIGRATION_SQL);
            await fixtureDb.exec(`
                INSERT INTO favorite_comedians (profile_id, comedian_id)
                VALUES ('new-profile', 'new-comedian');
            `);

            const result = await fixtureDb.query<{
                profile_id: string;
                created_at: Date | string | null;
            }>(
                "SELECT profile_id, created_at FROM favorite_comedians ORDER BY profile_id",
            );

            expect(result.rows[0]).toMatchObject({
                profile_id: "legacy-profile",
                created_at: null,
            });
            expect(result.rows[1]?.profile_id).toBe("new-profile");
            expect(result.rows[1]?.created_at).not.toBeNull();
        } finally {
            await fixtureDb.close();
        }
    });
});

describe("favorite growth aggregates", () => {
    let fixtureDb: PGlite;

    beforeAll(async () => {
        fixtureDb = new PGlite();
        await fixtureDb.exec(`
            CREATE TABLE favorite_comedians (
                profile_id TEXT NOT NULL,
                comedian_id TEXT NOT NULL,
                PRIMARY KEY (profile_id, comedian_id)
            );
        `);
        await fixtureDb.exec(MIGRATION_SQL);
    });

    afterAll(async () => {
        await fixtureDb.close();
    });

    beforeEach(async () => {
        vi.clearAllMocks();
        await fixtureDb.exec("TRUNCATE favorite_comedians");
    });

    it("uses trailing complete UTC days for recent and baseline windows", () => {
        expect(getFavoriteGrowthWindows(AS_OF)).toEqual({
            baselineStart: new Date("2026-06-18T00:00:00.000Z"),
            recentStart: new Date("2026-07-16T00:00:00.000Z"),
            end: new Date("2026-07-23T00:00:00.000Z"),
        });
    });

    it("counts exact recent and baseline boundaries and excludes incomplete, old, and legacy rows", async () => {
        await fixtureDb.query(
            `
            INSERT INTO favorite_comedians (profile_id, comedian_id, created_at)
            VALUES
                ('recent-start', 'comic-a', '2026-07-16T00:00:00Z'),
                ('recent-end', 'comic-a', '2026-07-22T23:59:59Z'),
                ('current-day', 'comic-a', '2026-07-23T00:00:00Z'),
                ('baseline-start', 'comic-a', '2026-06-18T00:00:00Z'),
                ('baseline-end', 'comic-a', '2026-07-15T23:59:59Z'),
                ('too-old', 'comic-a', '2026-06-17T23:59:59Z'),
                ('legacy', 'comic-a', NULL),
                ('other-recent', 'comic-b', '2026-07-20T12:00:00Z')
            `,
        );

        await expect(runAggregate(fixtureDb)).resolves.toEqual([
            { comedianId: "comic-a", recentCount: 2, baselineCount: 2 },
            { comedianId: "comic-b", recentCount: 1, baselineCount: 0 },
        ]);
    });

    it("preserves one favorite per profile and comedian", async () => {
        await fixtureDb.exec(`
            INSERT INTO favorite_comedians (profile_id, comedian_id, created_at)
            VALUES ('profile-1', 'comic-a', '2026-07-20T12:00:00Z');
        `);

        await expect(
            fixtureDb.exec(`
                INSERT INTO favorite_comedians (profile_id, comedian_id, created_at)
                VALUES ('profile-1', 'comic-a', '2026-07-21T12:00:00Z');
            `),
        ).rejects.toThrow();
    });

    it("removes an unfavorited relationship and measures a later re-favorite as new", async () => {
        await fixtureDb.exec(`
            INSERT INTO favorite_comedians (profile_id, comedian_id, created_at)
            VALUES ('profile-1', 'comic-a', '2026-06-20T12:00:00Z');
            DELETE FROM favorite_comedians
            WHERE profile_id = 'profile-1' AND comedian_id = 'comic-a';
        `);
        await expect(runAggregate(fixtureDb)).resolves.toEqual([]);

        await fixtureDb.exec(`
            INSERT INTO favorite_comedians (profile_id, comedian_id, created_at)
            VALUES ('profile-1', 'comic-a', '2026-07-20T12:00:00Z');
        `);
        await expect(runAggregate(fixtureDb)).resolves.toEqual([
            { comedianId: "comic-a", recentCount: 1, baselineCount: 0 },
        ]);
    });

    it("normalizes PostgreSQL bigint counts for feature computation", async () => {
        mockQueryRaw.mockResolvedValue([
            {
                comedian_id: "comic-a",
                recent_count: BigInt(3),
                baseline_count: BigInt(9),
            },
        ]);

        await expect(getFavoriteGrowth(AS_OF)).resolves.toEqual([
            { comedianId: "comic-a", recentCount: 3, baselineCount: 9 },
        ]);
    });
});
