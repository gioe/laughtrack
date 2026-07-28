import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const PRISMA_DIR = resolve(import.meta.dirname);
const SCHEMA_TEXT = readFileSync(resolve(PRISMA_DIR, "schema.prisma"), "utf-8");
const MIGRATION_SQL = readFileSync(
    resolve(
        PRISMA_DIR,
        "migrations/20260728003000_add_saved_shows/migration.sql",
    ),
    "utf-8",
);

describe("SavedShow schema contract", () => {
    it("defines a binary per-profile and show relation", () => {
        expect(SCHEMA_TEXT).toContain("model SavedShow");
        expect(SCHEMA_TEXT).toMatch(
            /profileId\s+String\s+@map\("profile_id"\)/,
        );
        expect(SCHEMA_TEXT).toMatch(/showId\s+Int\s+@map\("show_id"\)/);
        expect(SCHEMA_TEXT).toMatch(
            /createdAt\s+DateTime\s+@default\(now\(\)\)\s+@map\("created_at"\)\s+@db\.Timestamptz/,
        );
        expect(SCHEMA_TEXT).toContain("@@id([profileId, showId])");
        expect(SCHEMA_TEXT).toContain("@@index([showId])");
        expect(SCHEMA_TEXT).toContain('@@map("saved_shows")');
        expect(SCHEMA_TEXT).toMatch(
            /profile\s+UserProfile\s+@relation\(fields: \[profileId\], references: \[id\], onDelete: Cascade\)/,
        );
        expect(SCHEMA_TEXT).toMatch(
            /show\s+Show\s+@relation\(fields: \[showId\], references: \[id\], onDelete: Cascade\)/,
        );
        expect(SCHEMA_TEXT).toMatch(
            /model UserProfile \{[\s\S]*?savedShows\s+SavedShow\[\]/,
        );
        expect(SCHEMA_TEXT).toMatch(
            /model Show \{[\s\S]*?savedShows\s+SavedShow\[\]/,
        );
    });

    it("creates the table with uniqueness, timestamp, lookup index, and cascading foreign keys", () => {
        expect(MIGRATION_SQL).toContain('CREATE TABLE "saved_shows"');
        expect(MIGRATION_SQL).toContain(
            '"created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP',
        );
        expect(MIGRATION_SQL).toContain(
            'PRIMARY KEY ("profile_id", "show_id")',
        );
        expect(MIGRATION_SQL).toContain(
            'CREATE INDEX "saved_shows_show_id_idx" ON "saved_shows"("show_id")',
        );
        expect(MIGRATION_SQL).toMatch(
            /FOREIGN KEY \("profile_id"\) REFERENCES "user_profiles"\("id"\) ON DELETE CASCADE ON UPDATE CASCADE/,
        );
        expect(MIGRATION_SQL).toMatch(
            /FOREIGN KEY \("show_id"\) REFERENCES "shows"\("id"\) ON DELETE CASCADE ON UPDATE CASCADE/,
        );
    });
});
