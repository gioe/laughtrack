import { PGlite } from "@electric-sql/pglite";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";

const HERE = dirname(fileURLToPath(import.meta.url));

function loadMigrationSql(): string {
    const migrationsDir = resolve(HERE, "migrations");
    const suffix = "_add_ticket_purchase_click_events";
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
    CREATE TABLE users (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE
    );
    CREATE TABLE user_profiles (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL UNIQUE REFERENCES users(id)
    );
    CREATE TABLE clubs (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL
    );
    CREATE TABLE shows (
        id SERIAL PRIMARY KEY,
        club_id INTEGER NOT NULL REFERENCES clubs(id) ON DELETE CASCADE
    );
`;

describe("ticket_purchase_click_events migration", () => {
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
            "TRUNCATE ticket_purchase_click_events, shows, clubs, user_profiles, users RESTART IDENTITY CASCADE",
        );
    });

    it("stores show, club, optional profile, anonymous visitor, destination, surface, user-agent, device metadata, and timestamp", async () => {
        await db.query("INSERT INTO users (id, email) VALUES ($1, $2)", [
            "user-1",
            "user@example.com",
        ]);
        await db.query(
            "INSERT INTO user_profiles (id, user_id) VALUES ($1, $2)",
            ["profile-1", "user-1"],
        );
        await db.query("INSERT INTO clubs (id, name) VALUES ($1, $2)", [
            24,
            "The Copper Room",
        ]);
        await db.query(
            "INSERT INTO shows (id, club_id) VALUES ($1, $2)",
            [42, 24],
        );

        const result = await db.query<{
            show_id: number;
            club_id: number;
            profile_id: string | null;
            anonymous_visitor_id: string;
            destination_url: string;
            source_surface: string;
            user_agent: string;
            device_metadata: unknown;
            created_at: Date | string;
        }>(
            `
            INSERT INTO ticket_purchase_click_events (
                show_id,
                club_id,
                profile_id,
                anonymous_visitor_id,
                destination_url,
                source_surface,
                user_agent,
                device_metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING show_id, club_id, profile_id, anonymous_visitor_id, destination_url, source_surface, user_agent, device_metadata, created_at
            `,
            [
                42,
                24,
                "profile-1",
                "anon-123",
                "https://tickets.example.com/buy",
                "show_detail",
                "Vitest Browser",
                { platform: "web" },
            ],
        );

        expect(result.rows[0]).toMatchObject({
            show_id: 42,
            club_id: 24,
            profile_id: "profile-1",
            anonymous_visitor_id: "anon-123",
            destination_url: "https://tickets.example.com/buy",
            source_surface: "show_detail",
            user_agent: "Vitest Browser",
            device_metadata: { platform: "web" },
        });
        expect(new Date(result.rows[0].created_at).getTime()).toBeGreaterThan(
            0,
        );
    });

    it("deletes raw click events older than 13 months with the retention helper", async () => {
        await db.query("INSERT INTO clubs (id, name) VALUES ($1, $2)", [
            24,
            "The Copper Room",
        ]);
        await db.query(
            "INSERT INTO shows (id, club_id) VALUES ($1, $2)",
            [42, 24],
        );
        await db.query(
            `
            INSERT INTO ticket_purchase_click_events (
                show_id, club_id, anonymous_visitor_id, destination_url, source_surface, created_at
            )
            VALUES
                (42, 24, 'old-anon', 'https://tickets.example.com/old', 'show_detail', NOW() - INTERVAL '14 months'),
                (42, 24, 'fresh-anon', 'https://tickets.example.com/fresh', 'show_detail', NOW() - INTERVAL '12 months')
            `,
        );

        const deleted = await db.query<{ deleted_count: number }>(
            "SELECT cleanup_old_ticket_purchase_click_events() AS deleted_count",
        );
        const remaining = await db.query<{ anonymous_visitor_id: string }>(
            "SELECT anonymous_visitor_id FROM ticket_purchase_click_events",
        );

        expect(Number(deleted.rows[0].deleted_count)).toBe(1);
        expect(remaining.rows).toEqual([
            { anonymous_visitor_id: "fresh-anon" },
        ]);
    });
});
