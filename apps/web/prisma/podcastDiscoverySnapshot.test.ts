import { PGlite } from "@electric-sql/pglite";
import { readFileSync } from "node:fs";
import { afterAll, beforeAll, expect, it } from "vitest";

let db: PGlite;
beforeAll(async () => {
    db = new PGlite();
    await db.exec(`
        CREATE TABLE comedians (id int PRIMARY KEY, name text, visible boolean, parent_comedian_id int);
        CREATE TABLE comedian_deny_list (id int PRIMARY KEY, name text);
        CREATE TABLE podcast_deny_list (id int PRIMARY KEY, restored_at timestamptz);
        CREATE TABLE episode_appearances (id int PRIMARY KEY, comedian_id int, episode_id int, review_status text);
        CREATE TABLE podcasts (id int PRIMARY KEY, source text, source_podcast_id text, feed_url text);
        CREATE TABLE podcast_episodes (id int PRIMARY KEY);
        CREATE TABLE curation_entities (id text PRIMARY KEY, kind text);
        CREATE TABLE curation_relationships (id text PRIMARY KEY, kind text);
        CREATE TABLE curation_decisions (entity_id text, relationship_id text);
        INSERT INTO curation_entities VALUES ('podcast', 'podcast'), ('comedian', 'comedian'), ('club', 'club');
        INSERT INTO curation_relationships VALUES ('host', 'host_of'), ('alias', 'alias_of');
        INSERT INTO comedians VALUES (1, 'Avery', true, null);
        INSERT INTO episode_appearances VALUES (1, 1, 1, 'accepted');
        INSERT INTO podcasts VALUES (1, 'rss', '1', 'https://example.com');
        INSERT INTO podcast_episodes VALUES (1);
    `);
    await db.exec(
        readFileSync(
            new URL(
                "./migrations/20261010120000_podcast_discovery_snapshot/migration.sql",
                import.meta.url,
            ),
            "utf8",
        ),
    );
    await db.exec(
        readFileSync(
            new URL(
                "./migrations/20261026193000_podcast_snapshot_curation_invalidation/migration.sql",
                import.meta.url,
            ),
            "utf8",
        ),
    );
});
afterAll(async () => {
    await db?.close();
});
async function publish() {
    await db.exec(
        `UPDATE podcast_discovery_snapshots SET payload = '{"episodes":[{"id":1}]}', generated_at = NOW()`,
    );
    const { rows } = await db.query<{ revision: number }>(
        "SELECT revision FROM podcast_discovery_snapshots",
    );
    return rows[0].revision;
}
it("invalidates moderation changes and refuses a racing stale publication", async () => {
    for (const mutation of [
        "UPDATE comedians SET visible = false WHERE id = 1",
        "UPDATE comedians SET parent_comedian_id = 2 WHERE id = 1",
        "INSERT INTO comedian_deny_list VALUES (1, 'Avery')",
        "INSERT INTO podcast_deny_list VALUES (1, null)",
        "UPDATE episode_appearances SET review_status = 'denied' WHERE id = 1",
        "UPDATE podcasts SET feed_url = 'https://other.example.com' WHERE id = 1",
        "DELETE FROM podcast_episodes WHERE id = 1",
        "INSERT INTO curation_decisions VALUES ('podcast', null)",
        "INSERT INTO curation_decisions VALUES ('comedian', null)",
        "INSERT INTO curation_decisions VALUES (null, 'host')",
        "INSERT INTO curation_decisions VALUES (null, 'alias')",
    ]) {
        const revision = await publish();
        await db.exec(mutation);
        const { rows } = await db.query<{ payload: unknown }>(
            "SELECT payload FROM podcast_discovery_snapshots",
        );
        expect(rows[0].payload, mutation).toBeNull();
        const update = await db.query(
            "UPDATE podcast_discovery_snapshots SET payload = '{}' WHERE revision = $1",
            [revision],
        );
        expect(update.affectedRows).toBe(0);
    }
});
it("ignores no-op ingestion and updates that match no rows", async () => {
    const revision = await publish();
    await db.exec(`
        UPDATE comedians SET visible = visible;
        UPDATE episode_appearances SET review_status = review_status;
        UPDATE podcasts SET feed_url = feed_url;
        UPDATE comedians SET visible = true WHERE id = 999;
        INSERT INTO curation_decisions VALUES ('club', null);
    `);
    const { rows } = await db.query<{ revision: number; payload: unknown }>(
        "SELECT revision, payload FROM podcast_discovery_snapshots",
    );
    expect(rows[0].revision).toBe(revision);
    expect(rows[0].payload).not.toBeNull();
});
