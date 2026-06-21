import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

const migrationPath = path.join(
    process.cwd(),
    "prisma",
    "migrations",
    "20260621001000_add_venue_deny_list_evidence",
    "migration.sql",
);

describe("venue deny-list evidence migration", () => {
    const sql = () => fs.readFileSync(migrationPath, "utf8");

    it("adds structured evidence fields to venue_deny_list", () => {
        const migration = sql();

        expect(migration).toContain("google_primary_type");
        expect(migration).toContain("evidence");
        expect(migration).toContain("venue_deny_list");
    });

    it("backfills Google primary type evidence from legacy reason text", () => {
        const migration = sql();

        expect(migration).toContain("Google primary_type=");
        expect(migration).toContain("jsonb_build_object");
    });
});
