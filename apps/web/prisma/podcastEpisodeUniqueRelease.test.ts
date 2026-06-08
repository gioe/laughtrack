import { PGlite } from "@electric-sql/pglite";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";

const HERE = dirname(fileURLToPath(import.meta.url));

function loadMigrationSql(): string {
    const migrationsDir = resolve(HERE, "migrations");
    const suffix = "_add_podcast_episode_unique_release";
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
        id SERIAL PRIMARY KEY
    );

    CREATE TABLE podcast_episodes (
        id SERIAL PRIMARY KEY,
        podcast_id INTEGER NOT NULL REFERENCES podcasts(id) ON DELETE CASCADE,
        source TEXT NOT NULL,
        source_episode_id TEXT NOT NULL,
        guid TEXT,
        title TEXT NOT NULL,
        description TEXT,
        release_date TIMESTAMPTZ,
        duration_seconds INTEGER,
        episode_url TEXT,
        audio_url TEXT,
        external_ids JSONB NOT NULL DEFAULT '{}',
        evidence JSONB NOT NULL DEFAULT '{}',
        source_payload JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE UNIQUE INDEX podcast_episodes_source_episode_id_key
        ON podcast_episodes(source, source_episode_id);
`;

const UPSERT_SQL = `
    WITH inserted AS (
        INSERT INTO podcast_episodes (
            podcast_id,
            source,
            source_episode_id,
            guid,
            title,
            description,
            release_date,
            duration_seconds,
            episode_url,
            audio_url,
            external_ids,
            evidence,
            source_payload
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7::timestamptz, $8, $9, $10, $11::jsonb, $12::jsonb, $13::jsonb)
        ON CONFLICT DO NOTHING
        RETURNING id, true AS inserted, true AS changed
    ),
    target AS (
        SELECT
            id,
            (source = $2 AND source_episode_id = $3) AS same_source
        FROM podcast_episodes
        WHERE NOT EXISTS (SELECT 1 FROM inserted)
          AND (
            (source = $2 AND source_episode_id = $3)
            OR (
                $7::timestamptz IS NOT NULL
                AND podcast_id = $1
                AND release_date = $7::timestamptz
                AND LOWER(REGEXP_REPLACE(BTRIM(title), '^\\s*(?:(?:ep(?:isode)?|#)\\s*[0-9]+(?:\\s*[:.\\-\\)\\]]|\\s+)\\s*|[0-9]+\\s*[:.\\-\\)\\]]\\s*)', '', 'i'))
                    = LOWER(REGEXP_REPLACE(BTRIM($5), '^\\s*(?:(?:ep(?:isode)?|#)\\s*[0-9]+(?:\\s*[:.\\-\\)\\]]|\\s+)\\s*|[0-9]+\\s*[:.\\-\\)\\]]\\s*)', '', 'i'))
            )
          )
        ORDER BY CASE WHEN source = $2 AND source_episode_id = $3 THEN 0 ELSE 1 END, id
        LIMIT 1
    ),
    updated AS (
        UPDATE podcast_episodes
        SET podcast_id = $1,
            guid = COALESCE($4, podcast_episodes.guid),
            title = $5,
            description = $6,
            release_date = $7::timestamptz,
            duration_seconds = $8,
            episode_url = $9,
            audio_url = $10,
            external_ids = $11::jsonb,
            evidence = $12::jsonb,
            source_payload = $13::jsonb,
            updated_at = NOW()
        WHERE id = (SELECT id FROM target WHERE same_source)
          AND (
            podcast_episodes.podcast_id IS DISTINCT FROM $1
            OR podcast_episodes.guid IS DISTINCT FROM COALESCE($4, podcast_episodes.guid)
            OR podcast_episodes.title IS DISTINCT FROM $5
            OR podcast_episodes.description IS DISTINCT FROM $6
            OR podcast_episodes.release_date IS DISTINCT FROM $7::timestamptz
            OR podcast_episodes.duration_seconds IS DISTINCT FROM $8
            OR podcast_episodes.episode_url IS DISTINCT FROM $9
            OR podcast_episodes.audio_url IS DISTINCT FROM $10
            OR podcast_episodes.external_ids IS DISTINCT FROM $11::jsonb
            OR podcast_episodes.evidence IS DISTINCT FROM $12::jsonb
            OR podcast_episodes.source_payload IS DISTINCT FROM $13::jsonb
          )
        RETURNING id, false AS inserted, true AS changed
    ),
    unchanged AS (
        SELECT id, false AS inserted, false AS changed
        FROM target
        WHERE NOT EXISTS (SELECT 1 FROM updated)
    )
    SELECT id, inserted, changed FROM inserted
    UNION ALL
    SELECT id, inserted, changed FROM updated
    UNION ALL
    SELECT id, inserted, changed FROM unchanged
    LIMIT 1
`;

async function upsertEpisode(
    db: PGlite,
    sourceEpisodeId: string,
    title = `Episode ${sourceEpisodeId}`,
): Promise<{ id: number; inserted: boolean; changed: boolean }> {
    const res = await db.query<{
        id: number;
        inserted: boolean;
        changed: boolean;
    }>(UPSERT_SQL, [
        1,
        "rss",
        sourceEpisodeId,
        sourceEpisodeId,
        title,
        null,
        "2026-06-08T12:00:00+00:00",
        null,
        null,
        null,
        "{}",
        "{}",
        "{}",
    ]);
    return res.rows[0];
}

describe("podcast episode unique release migration", () => {
    let db: PGlite;

    beforeAll(async () => {
        db = new PGlite();
        await db.exec(BASE_SCHEMA_SQL);
        await db.exec(MIGRATION_SQL);
    });

    afterAll(async () => {
        await db.close();
    });

    beforeEach(async () => {
        await db.exec(
            "TRUNCATE podcast_episodes, podcasts RESTART IDENTITY CASCADE",
        );
        await db.query("INSERT INTO podcasts DEFAULT VALUES");
    });

    it("collapses concurrent logical inserts for the same podcast release and normalized title into one row", async () => {
        const [first, second] = await Promise.all([
            upsertEpisode(db, "source-a", "Episode One"),
            upsertEpisode(db, "source-b", "67: Episode One"),
        ]);

        const count = await db.query<{ count: number }>(
            "SELECT COUNT(*)::int AS count FROM podcast_episodes",
        );

        expect(count.rows[0].count).toBe(1);
        expect(first.id).toBe(second.id);
        expect([first.inserted, second.inserted].filter(Boolean)).toHaveLength(
            1,
        );
    });

    it("allows distinct titles on the same podcast release timestamp", async () => {
        const [first, second] = await Promise.all([
            upsertEpisode(db, "source-a", "THAT in THIS!"),
            upsertEpisode(db, "source-b", "Let's do this!"),
        ]);

        const rows = await db.query<{ title: string }>(
            "SELECT title FROM podcast_episodes ORDER BY id",
        );

        expect(rows.rows.map((row) => row.title)).toEqual([
            "THAT in THIS!",
            "Let's do this!",
        ]);
        expect(first.id).not.toBe(second.id);
        expect(first.inserted).toBe(true);
        expect(second.inserted).toBe(true);
    });

    it("does not treat NULL release dates as logical duplicates", async () => {
        await db.query(
            "INSERT INTO podcast_episodes (podcast_id, source, source_episode_id, title) VALUES (1, 'rss', 'null-a', 'A')",
        );
        await db.query(
            "INSERT INTO podcast_episodes (podcast_id, source, source_episode_id, title) VALUES (1, 'rss', 'null-b', 'B')",
        );

        const count = await db.query<{ count: number }>(
            "SELECT COUNT(*)::int AS count FROM podcast_episodes",
        );

        expect(count.rows[0].count).toBe(2);
    });
});
