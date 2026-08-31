import { PGlite } from "@electric-sql/pglite";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

const HERE = dirname(fileURLToPath(import.meta.url));

function loadMigrationSql(): string {
    const migrationsDir = resolve(HERE, "migrations");
    const suffix = "_repair_existing_comedian_visibility_blocks";
    const matches = readdirSync(migrationsDir).filter((entry) =>
        entry.endsWith(suffix),
    );
    if (matches.length !== 1) {
        throw new Error(
            `Expected exactly one migration ending in '${suffix}', found ${matches.length}`,
        );
    }
    return readFileSync(
        resolve(migrationsDir, matches[0], "migration.sql"),
        "utf8",
    );
}

describe("comedian visibility block consolidation", () => {
    let db: PGlite;

    beforeAll(async () => {
        db = new PGlite();
        await db.exec(`
            CREATE TABLE comedians (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                visible BOOLEAN NOT NULL DEFAULT true
            );
            CREATE TABLE comedian_deny_list (
                name TEXT PRIMARY KEY,
                reason TEXT NOT NULL DEFAULT '',
                deleted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                added_by TEXT NOT NULL DEFAULT 'audit_script'
            );
        `);
        await db.query("INSERT INTO comedians (name) VALUES ($1), ($2)", [
            "Carie Karavas",
            "Visible Comic",
        ]);
        await db.query(
            `INSERT INTO comedian_deny_list (name, reason, added_by, deleted_at)
             VALUES ($1, $2, $3, $4), ($5, $6, $7, $8), ($9, $10, $11, $12)`,
            [
                "  CARIE\u00a0Karavas ",
                "older identity block",
                "profile-1",
                "2026-08-26T12:00:00Z",
                "carie karavas",
                "existing identity block",
                "profile-3",
                "2026-08-27T12:00:00Z",
                "Open Mic Showcase",
                "orphan event title",
                "profile-2",
                "2026-08-27T13:00:00Z",
            ],
        );
        await db.exec(loadMigrationSql());
    });

    afterAll(async () => {
        await db.close();
    });

    it("hides overlaps, preserves audit metadata, and leaves orphans unchanged", async () => {
        const comedians = await db.query<{
            name: string;
            visible: boolean;
            block_reason: string | null;
            block_added_by: string | null;
            block_added_at: Date | string | null;
        }>(
            `SELECT name, visible, block_reason, block_added_by, block_added_at
             FROM comedians ORDER BY name`,
        );
        expect(comedians.rows[0]).toMatchObject({
            name: "Carie Karavas",
            visible: false,
            block_reason: "existing identity block",
            block_added_by: "profile-3",
        });
        expect(new Date(comedians.rows[0].block_added_at!).toISOString()).toBe(
            "2026-08-27T12:00:00.000Z",
        );
        expect(comedians.rows[1]).toMatchObject({
            name: "Visible Comic",
            visible: true,
            block_reason: null,
        });

        const denyRows = await db.query<{ name: string; reason: string }>(
            "SELECT name, reason FROM comedian_deny_list ORDER BY name",
        );
        expect(denyRows.rows).toEqual([
            { name: "Open Mic Showcase", reason: "orphan event title" },
        ]);

        const archive = await db.query<{
            comedian_id: number;
            name: string;
            reason: string;
            added_by: string;
        }>(
            "SELECT comedian_id, name, reason, added_by FROM comedian_visibility_block_archive",
        );
        expect(archive.rows).toHaveLength(2);
        expect(archive.rows).toEqual(
            expect.arrayContaining([
                expect.objectContaining({
                    comedian_id: 1,
                    name: "  CARIE\u00a0Karavas ",
                    reason: "older identity block",
                    added_by: "profile-1",
                }),
                expect.objectContaining({
                    comedian_id: 1,
                    name: "carie karavas",
                    reason: "existing identity block",
                    added_by: "profile-3",
                }),
            ]),
        );
    });
});
