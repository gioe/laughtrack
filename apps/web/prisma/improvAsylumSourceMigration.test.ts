import { PGlite } from "@electric-sql/pglite";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";

const HERE = dirname(fileURLToPath(import.meta.url));
const MIGRATION_SQL = readFileSync(
    resolve(
        HERE,
        "migrations/20260811110000_restore_improv_asylum_tixr_source/migration.sql",
    ),
    "utf8",
);

describe("Improv Asylum scraping source correction", () => {
    let db: PGlite;

    beforeAll(async () => {
        db = new PGlite();
    });

    afterAll(async () => {
        await db.close();
    });

    beforeEach(async () => {
        await db.exec("DROP TABLE IF EXISTS scraping_sources");
        await db.exec(`
            CREATE TABLE scraping_sources (
                id SERIAL PRIMARY KEY,
                club_id INTEGER,
                platform TEXT NOT NULL,
                scraper_key TEXT NOT NULL,
                source_url TEXT,
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        `);
    });

    it("repoints the stale dedicated source to the generic Tixr fallback", async () => {
        await db.exec(`
            INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url)
            VALUES (
                141,
                'custom',
                'improv_asylum',
                'https://calendar.improvasylum.com/api/events/improv-asylum'
            );
        `);

        await db.exec(MIGRATION_SQL);

        const result = await db.query<{
            platform: string;
            scraper_key: string;
            source_url: string;
        }>("SELECT platform, scraper_key, source_url FROM scraping_sources");

        expect(result.rows).toEqual([
            {
                platform: "tixr",
                scraper_key: "tixr",
                source_url: "https://www.tixr.com/groups/improvasylum",
            },
        ]);
    });

    it("does not rewrite unrelated or disabled sources", async () => {
        await db.exec(`
            INSERT INTO scraping_sources (club_id, platform, scraper_key, source_url, enabled)
            VALUES
                (999, 'custom', 'improv_asylum', 'https://calendar.improvasylum.com/api/events/improv-asylum', TRUE),
                (141, 'custom', 'improv_asylum', 'https://calendar.improvasylum.com/api/events/improv-asylum', FALSE);
        `);

        await db.exec(MIGRATION_SQL);

        const result = await db.query<{
            club_id: number;
            enabled: boolean;
            scraper_key: string;
        }>(
            "SELECT club_id, enabled, scraper_key FROM scraping_sources ORDER BY id",
        );

        expect(result.rows).toEqual([
            { club_id: 999, enabled: true, scraper_key: "improv_asylum" },
            { club_id: 141, enabled: false, scraper_key: "improv_asylum" },
        ]);
    });
});
