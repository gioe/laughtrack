import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

const migrationPath = path.join(
    process.cwd(),
    "prisma",
    "migrations",
    "20260620040000_add_source_targets",
    "migration.sql",
);

describe("source targets migration", () => {
    const sql = () => fs.readFileSync(migrationPath, "utf8");

    it("creates source_targets for non-venue scraper trigger identity", () => {
        const migration = sql();

        expect(migration).toContain("CREATE TABLE source_targets");
        expect(migration).toContain("target_type TEXT NOT NULL");
        expect(migration).toContain('platform "ScrapingPlatform"');
        expect(migration).toContain("metadata JSONB NOT NULL DEFAULT '{}'::jsonb");
        expect(migration).toContain("CREATE UNIQUE INDEX source_targets_slug_key");
    });

    it("lets scraping_sources belong to exactly one target owner", () => {
        const migration = sql();

        expect(migration).toContain("ADD COLUMN source_target_id INTEGER");
        expect(migration).toContain("FOREIGN KEY (source_target_id) REFERENCES source_targets(id)");
        expect(migration).toContain("(club_id IS NOT NULL AND source_target_id IS NULL)");
        expect(migration).toContain("(club_id IS NULL AND source_target_id IS NOT NULL)");
        expect(migration).toContain("scraping_sources_source_target_platform_priority_key");
    });

    it("migrates the Ticketmaster National trigger out of clubs", () => {
        const migration = sql();

        expect(migration).toContain("ticketmaster-national");
        expect(migration).toContain("UPDATE scraping_sources ss");
        expect(migration).toContain("SET source_target_id = st.id");
        expect(migration).toContain("DELETE FROM clubs WHERE id = 4036");
    });
});
