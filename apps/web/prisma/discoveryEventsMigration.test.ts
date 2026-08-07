import { PGlite } from "@electric-sql/pglite";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";

const HERE = dirname(fileURLToPath(import.meta.url));
const MIGRATION_SQL = readFileSync(
    resolve(
        HERE,
        "migrations/20260723131000_add_discovery_impression_events/migration.sql",
    ),
    "utf-8",
);
const RAIL_IMPRESSIONS_MIGRATION_SQL = readFileSync(
    resolve(
        HERE,
        "migrations/20260807181500_allow_discovery_rail_impressions/migration.sql",
    ),
    "utf-8",
);

const BASE_SCHEMA_SQL = `
    CREATE TABLE user_profiles (id TEXT PRIMARY KEY);
    CREATE TABLE ticket_purchase_click_events (
        id SERIAL PRIMARY KEY,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
`;

const IMPRESSION_COLUMNS = `
    event_id, entity_type, entity_id, surface, policy_version,
    experiment_variant, rank, impressed_at, anonymous_visitor_id
`;

describe("discovery event migration", () => {
    let db: PGlite;

    beforeAll(async () => {
        db = new PGlite();
        await db.exec(BASE_SCHEMA_SQL);
        await db.exec(MIGRATION_SQL);
        await db.exec(RAIL_IMPRESSIONS_MIGRATION_SQL);
    });

    afterAll(async () => {
        await db.close();
    });

    beforeEach(async () => {
        await db.exec(
            "TRUNCATE discovery_impression_events, ticket_purchase_click_events, user_profiles CASCADE",
        );
    });

    it("stores an indexed qualified impression and rejects invalid dimensions", async () => {
        await db.query(
            `INSERT INTO discovery_impression_events (${IMPRESSION_COLUMNS})
             VALUES ($1, 'show', 42, 'near_you', 'near-you-v1', 'candidate', 3, NOW(), 'anon-1')`,
            ["123e4567-e89b-42d3-a456-426614174000"],
        );

        const indexes = await db.query<{ indexname: string }>(
            `SELECT indexname
             FROM pg_indexes
             WHERE tablename = 'discovery_impression_events'`,
        );
        expect(indexes.rows.map((row) => row.indexname)).toEqual(
            expect.arrayContaining([
                "discovery_impression_events_surface_variant_time_idx",
                "discovery_impression_events_entity_time_idx",
                "discovery_impression_events_recorded_at_idx",
            ]),
        );

        await expect(
            db.query(
                `INSERT INTO discovery_impression_events (${IMPRESSION_COLUMNS})
                 VALUES ($1, 'show', 42, 'search', 'near-you-v1', 'candidate', 0, NOW(), 'anon-1')`,
                ["123e4567-e89b-42d3-a456-426614174001"],
            ),
        ).rejects.toThrow();
    });

    it("uses event UUIDs as idempotency keys", async () => {
        const eventId = "123e4567-e89b-42d3-a456-426614174002";
        const insert = `INSERT INTO discovery_impression_events (${IMPRESSION_COLUMNS})
            VALUES ($1, 'show', 42, 'near_you', 'near-you-v1', 'control', 1, NOW(), 'anon-1')
            ON CONFLICT ("event_id") DO NOTHING`;

        await db.query(insert, [eventId]);
        await db.query(insert, [eventId]);

        const count = await db.query<{ count: string }>(
            "SELECT COUNT(*)::text AS count FROM discovery_impression_events",
        );
        expect(count.rows[0].count).toBe("1");
    });

    it("stores server-directed rail impressions and rejects mismatched variants", async () => {
        await db.query(
            `INSERT INTO discovery_impression_events (${IMPRESSION_COLUMNS})
             VALUES ($1, 'show', 42, 'starting_to_buzz', '2', 'server_directed', 3, NOW(), 'anon-1')`,
            ["123e4567-e89b-42d3-a456-426614174005"],
        );

        await expect(
            db.query(
                `INSERT INTO discovery_impression_events (${IMPRESSION_COLUMNS})
                 VALUES ($1, 'show', 42, 'starting_to_buzz', '2', 'candidate', 3, NOW(), 'anon-1')`,
                ["123e4567-e89b-42d3-a456-426614174006"],
            ),
        ).rejects.toThrow();
        await expect(
            db.query(
                `INSERT INTO discovery_impression_events (${IMPRESSION_COLUMNS})
                 VALUES ($1, 'show', 42, 'near_you', 'near-you-v1', 'server_directed', 3, NOW(), 'anon-1')`,
                ["123e4567-e89b-42d3-a456-426614174007"],
            ),
        ).rejects.toThrow();
    });

    it("cascades engagement cleanup and retains denormalized ticket attribution", async () => {
        const eventId = "123e4567-e89b-42d3-a456-426614174003";
        await db.query(
            `INSERT INTO discovery_impression_events (${IMPRESSION_COLUMNS}, recorded_at)
             VALUES ($1, 'show', 42, 'near_you', 'near-you-v1', 'candidate', 2, NOW(), 'anon-1', NOW() - INTERVAL '14 months')`,
            [eventId],
        );
        await db.query(
            `INSERT INTO discovery_engagement_events
                (event_id, impression_event_id, engagement_type, engaged_at)
             VALUES ($1, $2, 'show_detail', NOW())`,
            ["123e4567-e89b-42d3-a456-426614174004", eventId],
        );
        await db.query(
            `INSERT INTO ticket_purchase_click_events
                (discovery_impression_event_id, discovery_surface,
                 discovery_policy_version, discovery_experiment_variant, discovery_rank)
             VALUES ($1, 'near_you', 'near-you-v1', 'candidate', 2)`,
            [eventId],
        );

        const deleted = await db.query<{ deleted_count: number }>(
            "SELECT cleanup_old_discovery_events() AS deleted_count",
        );
        const engagements = await db.query<{ count: string }>(
            "SELECT COUNT(*)::text AS count FROM discovery_engagement_events",
        );
        const clicks = await db.query<{ event_id: string }>(
            `SELECT discovery_impression_event_id::text AS event_id
             FROM ticket_purchase_click_events`,
        );

        expect(Number(deleted.rows[0].deleted_count)).toBe(1);
        expect(engagements.rows[0].count).toBe("0");
        expect(clicks.rows[0].event_id).toBe(eventId);
    });
});
