import { PGlite } from "@electric-sql/pglite";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";

const HERE = dirname(fileURLToPath(import.meta.url));

function loadMigrationSql(): string {
    const migrationsDir = resolve(HERE, "migrations");
    const suffix = "_add_podcast_slug";
    const matches = readdirSync(migrationsDir).filter((entry) =>
        entry.endsWith(suffix),
    );
    if (matches.length !== 1) {
        throw new Error(
            `Expected exactly one migration directory ending in '${suffix}', found ${matches.length}: ${matches.join(", ")}`,
        );
    }
    return readFileSync(
        resolve(migrationsDir, matches[0], "migration.sql"),
        "utf-8",
    );
}

const MIGRATION_SQL = loadMigrationSql();

const BASE_SCHEMA_SQL = `
    CREATE TABLE podcasts (
        id SERIAL PRIMARY KEY,
        source TEXT NOT NULL,
        source_podcast_id TEXT NOT NULL,
        title TEXT NOT NULL,
        evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE UNIQUE INDEX podcasts_source_podcast_id_key
        ON podcasts(source, source_podcast_id);
`;

describe("podcast slug migration", () => {
    let db: PGlite;

    beforeAll(async () => {
        db = new PGlite();
    });

    afterAll(async () => {
        await db.close();
    });

    beforeEach(async () => {
        await db.exec("DROP TABLE IF EXISTS podcasts");
        await db.exec(BASE_SCHEMA_SQL);
    });

    it("backfills non-null unique slugs from podcast title and source id", async () => {
        await db.exec(`
            INSERT INTO podcasts (source, source_podcast_id, title)
            VALUES
                ('podcast_index', 'feed-1', 'The Pod!'),
                ('podcast_index', 'feed-2', 'The Pod!')
        `);

        await db.exec(MIGRATION_SQL);

        const rows = await db.query<{ slug: string }>(
            "SELECT slug FROM podcasts ORDER BY id",
        );
        expect(rows.rows.map((row) => row.slug)).toEqual([
            "the-pod-feed-1",
            "the-pod-feed-2",
        ]);

        await expect(
            db.query(
                "INSERT INTO podcasts (source, source_podcast_id, title, slug) VALUES ('podcast_index', 'feed-3', 'Other Pod', NULL)",
            ),
        ).rejects.toThrow();
        await expect(
            db.query(
                "INSERT INTO podcasts (source, source_podcast_id, title, slug) VALUES ('podcast_index', 'feed-4', 'Other Pod', 'the-pod-feed-1')",
            ),
        ).rejects.toThrow();
    });
});
