import { PGlite } from "@electric-sql/pglite";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";

const HERE = dirname(fileURLToPath(import.meta.url));

function loadMigrationSql(): string {
    const migrationsDir = resolve(HERE, "migrations");
    const suffix = "_add_admin_action_audit_logging";
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
        role TEXT NOT NULL DEFAULT 'user',
        user_id TEXT NOT NULL UNIQUE REFERENCES users(id)
    );
`;

describe("admin_action_audits migration", () => {
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
            "TRUNCATE admin_action_audits, user_profiles, users RESTART IDENTITY CASCADE",
        );
    });

    it("stores actor, action, entity, reason, before/after JSON, and timestamp", async () => {
        await db.query("INSERT INTO users (id, email) VALUES ($1, $2)", [
            "user-1",
            "admin@example.com",
        ]);
        await db.query(
            "INSERT INTO user_profiles (id, role, user_id) VALUES ($1, $2, $3)",
            ["profile-1", "admin", "user-1"],
        );

        const res = await db.query<{
            actor_profile_id: string;
            action: string;
            entity_type: string;
            entity_id: string;
            reason: string;
            before_json: unknown;
            after_json: unknown;
            created_at: Date | string;
        }>(
            `
            INSERT INTO admin_action_audits (
                actor_profile_id,
                action,
                entity_type,
                entity_id,
                reason,
                before_json,
                after_json
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING actor_profile_id, action, entity_type, entity_id, reason, before_json, after_json, created_at
            `,
            [
                "profile-1",
                "club.update",
                "club",
                "42",
                "refresh venue metadata",
                { description: "old" },
                { description: "new" },
            ],
        );

        expect(res.rows[0]).toMatchObject({
            actor_profile_id: "profile-1",
            action: "club.update",
            entity_type: "club",
            entity_id: "42",
            reason: "refresh venue metadata",
            before_json: { description: "old" },
            after_json: { description: "new" },
        });
        expect(new Date(res.rows[0].created_at).getTime()).toBeGreaterThan(0);
    });

    it("preserves audit rows when an actor profile is deleted", async () => {
        await db.query("INSERT INTO users (id, email) VALUES ($1, $2)", [
            "user-1",
            "admin@example.com",
        ]);
        await db.query(
            "INSERT INTO user_profiles (id, role, user_id) VALUES ($1, $2, $3)",
            ["profile-1", "admin", "user-1"],
        );
        await db.query(
            `
            INSERT INTO admin_action_audits (
                actor_profile_id, action, entity_type, entity_id, before_json, after_json
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            `,
            ["profile-1", "club.update", "club", "42", {}, {}],
        );

        await db.query("DELETE FROM user_profiles WHERE id = $1", [
            "profile-1",
        ]);

        const res = await db.query<{ actor_profile_id: string | null }>(
            "SELECT actor_profile_id FROM admin_action_audits",
        );
        expect(res.rows[0].actor_profile_id).toBeNull();
    });
});
