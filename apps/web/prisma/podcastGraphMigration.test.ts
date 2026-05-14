import { PGlite } from "@electric-sql/pglite";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";

const HERE = dirname(fileURLToPath(import.meta.url));

function loadMigrationSql(): string {
    const migrationsDir = resolve(HERE, "migrations");
    const suffix = "_add_podcast_graph_tables";
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
    CREATE TABLE comedians (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL
    );

    CREATE TABLE comedian_podcast_appearances (
        id SERIAL PRIMARY KEY,
        comedian_id INTEGER NOT NULL REFERENCES comedians(id) ON DELETE CASCADE,
        source TEXT NOT NULL,
        source_episode_id TEXT NOT NULL,
        podcast_name TEXT NOT NULL,
        episode_title TEXT NOT NULL,
        release_date TIMESTAMPTZ,
        episode_url TEXT NOT NULL,
        match_confidence DOUBLE PRECISION NOT NULL,
        match_evidence JSONB NOT NULL,
        match_reviewed_at TIMESTAMPTZ,
        match_reviewed_by TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
`;

async function expectRejects(db: PGlite, sql: string, params: unknown[] = []) {
    await expect(db.query(sql, params)).rejects.toThrow();
}

describe("podcast graph migration", () => {
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
        await db.exec(`
            TRUNCATE
                episode_appearance_reviews,
                episode_appearances,
                podcast_candidate_reviews,
                comedian_podcasts,
                podcast_episodes,
                podcasts,
                comedian_podcast_appearances,
                comedians
            RESTART IDENTITY CASCADE
        `);
    });

    it("normalizes podcast and episode identity without duplicating episodes per comedian", async () => {
        await db.exec("INSERT INTO comedians (name) VALUES ('A'), ('B')");
        const podcast = await db.query<{ id: number }>(
            `
                INSERT INTO podcasts (source, source_podcast_id, feed_url, title, evidence)
                VALUES ('podcast_index', 'feed-1', 'https://example.com/feed.xml', 'The Pod', '{"provider": "podcast_index"}')
                RETURNING id
            `,
        );
        const podcastId = podcast.rows[0].id;
        const episode = await db.query<{ id: number }>(
            `
                INSERT INTO podcast_episodes (podcast_id, source, source_episode_id, guid, title, episode_url, evidence)
                VALUES ($1, 'podcast_index', 'episode-1', 'guid-1', 'Episode One', 'https://example.com/e/1', '{"matched_title": true}')
                RETURNING id
            `,
            [podcastId],
        );
        const episodeId = episode.rows[0].id;

        await db.query(
            `
                INSERT INTO episode_appearances
                    (comedian_id, episode_id, source, appearance_role, review_status, confidence, evidence)
                VALUES
                    (1, $1, 'podcast_index', 'guest', 'accepted', 0.92, '{"name_match": true}'),
                    (2, $1, 'podcast_index', 'guest', 'accepted', 0.88, '{"name_match": true}')
            `,
            [episodeId],
        );

        const count = await db.query<{ count: string }>(
            "SELECT COUNT(*) FROM podcast_episodes WHERE source_episode_id = 'episode-1'",
        );
        expect(Number(count.rows[0].count)).toBe(1);
    });

    it("keeps comedian-podcast host associations separate from episode guest appearances", async () => {
        await db.exec("INSERT INTO comedians (name) VALUES ('Host')");
        const podcast = await db.query<{ id: number }>(
            `
                INSERT INTO podcasts (source, source_podcast_id, title, evidence)
                VALUES ('podcast_index', 'feed-hosted', 'Hosted Show', '{}')
                RETURNING id
            `,
        );

        await db.query(
            `
                INSERT INTO comedian_podcasts
                    (comedian_id, podcast_id, association_type, source, review_status, confidence, evidence)
                VALUES (1, $1, 'host', 'podcast_index', 'accepted', 1, '{"host_claim": true}')
            `,
            [podcast.rows[0].id],
        );

        const appearances = await db.query<{ count: string }>(
            "SELECT COUNT(*) FROM episode_appearances WHERE comedian_id = 1",
        );
        expect(Number(appearances.rows[0].count)).toBe(0);
    });

    it("stores accepted and rejected podcast and episode appearance review candidates", async () => {
        await db.exec("INSERT INTO comedians (name) VALUES ('Candidate')");
        const podcast = await db.query<{ id: number }>(
            `
                INSERT INTO podcasts (source, source_podcast_id, title, evidence)
                VALUES ('podcast_index', 'feed-candidate', 'Candidate Pod', '{}')
                RETURNING id
            `,
        );
        const podcastId = podcast.rows[0].id;
        const episode = await db.query<{ id: number }>(
            `
                INSERT INTO podcast_episodes (podcast_id, source, source_episode_id, title, evidence)
                VALUES ($1, 'podcast_index', 'candidate-episode', 'Candidate Episode', '{}')
                RETURNING id
            `,
            [podcastId],
        );

        await db.query(
            `
                INSERT INTO podcast_candidate_reviews
                    (comedian_id, podcast_id, source, source_podcast_id, candidate_status, confidence, evidence)
                VALUES
                    (1, $1, 'podcast_index', 'feed-candidate', 'accepted', 0.9, '{"reason": "host bio"}'),
                    (1, NULL, 'podcast_index', 'feed-rejected', 'rejected', 0.2, '{"reason": "different person"}')
            `,
            [podcastId],
        );
        await db.query(
            `
                INSERT INTO episode_appearance_reviews
                    (comedian_id, episode_id, source, source_episode_id, candidate_status, appearance_role, confidence, evidence)
                VALUES
                    (1, $1, 'podcast_index', 'candidate-episode', 'accepted', 'guest', 0.85, '{"reason": "title mention"}'),
                    (1, NULL, 'podcast_index', 'rejected-episode', 'rejected', 'guest', 0.1, '{"reason": "name collision"}')
            `,
            [episode.rows[0].id],
        );

        const podcastStatuses = await db.query<{ candidate_status: string }>(
            "SELECT candidate_status FROM podcast_candidate_reviews ORDER BY id",
        );
        expect(podcastStatuses.rows.map((row) => row.candidate_status)).toEqual([
            "accepted",
            "rejected",
        ]);

        const episodeStatuses = await db.query<{ candidate_status: string }>(
            "SELECT candidate_status FROM episode_appearance_reviews ORDER BY id",
        );
        expect(episodeStatuses.rows.map((row) => row.candidate_status)).toEqual([
            "accepted",
            "rejected",
        ]);
    });

    it("enforces graph constraints while preserving the legacy appearance table", async () => {
        await db.exec("INSERT INTO comedians (name) VALUES ('Legacy')");
        const podcast = await db.query<{ id: number }>(
            `
                INSERT INTO podcasts (source, source_podcast_id, title, evidence)
                VALUES ('podcast_index', 'feed-unique', 'Unique Pod', '{}')
                RETURNING id
            `,
        );
        const podcastId = podcast.rows[0].id;
        const episode = await db.query<{ id: number }>(
            `
                INSERT INTO podcast_episodes (podcast_id, source, source_episode_id, title, evidence)
                VALUES ($1, 'podcast_index', 'episode-unique', 'Unique Episode', '{}')
                RETURNING id
            `,
            [podcastId],
        );

        await expectRejects(
            db,
            "INSERT INTO podcasts (source, source_podcast_id, title, evidence) VALUES ('podcast_index', 'feed-unique', 'Duplicate Pod', '{}')",
        );
        await expectRejects(
            db,
            "INSERT INTO podcast_episodes (podcast_id, source, source_episode_id, title, evidence) VALUES ($1, 'podcast_index', 'episode-unique', 'Duplicate Episode', '{}')",
            [podcastId],
        );
        await expectRejects(
            db,
            `
                INSERT INTO episode_appearances
                    (comedian_id, episode_id, source, review_status, confidence, evidence)
                VALUES (1, $1, 'podcast_index', 'maybe', 0.5, '{}')
            `,
            [episode.rows[0].id],
        );

        await db.query(
            `
                INSERT INTO comedian_podcast_appearances
                    (comedian_id, source, source_episode_id, podcast_name, episode_title, episode_url, match_confidence, match_evidence)
                VALUES (1, 'podcast_index', 'legacy-episode', 'Legacy Pod', 'Legacy Episode', 'https://example.com/legacy', 0.75, '{}')
            `,
        );
        const legacy = await db.query<{ count: string }>(
            "SELECT COUNT(*) FROM comedian_podcast_appearances",
        );
        expect(Number(legacy.rows[0].count)).toBe(1);
    });
});
