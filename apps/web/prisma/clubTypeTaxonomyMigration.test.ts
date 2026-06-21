import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";

const migrationPath = path.join(
    process.cwd(),
    "prisma",
    "migrations",
    "20260621000000_formalize_club_type_taxonomy",
    "migration.sql",
);

describe("club type taxonomy migration", () => {
    const sql = () => fs.readFileSync(migrationPath, "utf8");

    it("enforces the accepted club_type taxonomy", () => {
        const migration = sql();

        for (const clubType of [
            "club",
            "venue",
            "festival",
            "producer",
            "secret_location",
            "non_comedy",
        ]) {
            expect(migration).toContain(`'${clubType}'`);
        }
        expect(migration).toContain("clubs_club_type_check");
        expect(migration).toContain("CHECK (club_type IN");
    });

    it("backfills denied discovery placeholder rows as non_comedy", () => {
        const migration = sql();

        expect(migration).toContain("UPDATE clubs");
        expect(migration).toContain("venue_deny_list");
        expect(migration).toContain("club_type = 'non_comedy'");
    });

    it("maps legacy theater rows into venue before adding the constraint", () => {
        const migration = sql();

        expect(migration).toContain("club_type = 'venue'");
        expect(migration).toContain("club_type = 'theater'");
    });
});
