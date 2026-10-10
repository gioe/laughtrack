import { PGlite } from "@electric-sql/pglite";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

const HERE = dirname(fileURLToPath(import.meta.url));
const migration = readFileSync(
    resolve(
        HERE,
        "migrations/20261010210000_add_source_comedy_policies/migration.sql",
    ),
    "utf8",
);
const legacySchema = `CREATE TABLE scraping_sources (
 id SERIAL PRIMARY KEY, club_id INTEGER, source_target_id INTEGER,
 platform TEXT NOT NULL, scraper_key TEXT NOT NULL, priority INTEGER NOT NULL DEFAULT 0,
 enabled BOOLEAN NOT NULL DEFAULT TRUE);`;

describe("source comedy policy migration", () => {
    let db: PGlite;
    beforeEach(async () => {
        db = new PGlite();
        await db.exec(legacySchema);
    });
    afterEach(async () => {
        await db.close();
    });
    const seed = async () => {
        await db.exec(`INSERT INTO scraping_sources(id, club_id, source_target_id, platform, scraper_key, enabled) VALUES
   (1, 10, NULL, 'custom', 'first', true), (2, 10, NULL, 'custom', 'sibling', false),
   (3, NULL, 20, 'custom', 'aggregate', true)`);
        await db.exec(migration);
    };
    const row = async (id = 1) =>
        (
            await db.query<Record<string, unknown>>(
                "SELECT * FROM scraping_sources WHERE id = $1",
                [id],
            )
        ).rows[0];
    const change = async (
        mode = "shadow",
        evidence = { reason: "calendar review" },
    ) =>
        db.query(
            `UPDATE scraping_sources SET
   comedy_policy='mixed', comedy_gate_mode=$1, comedy_reviewed_by='operator', comedy_review_evidence=$2::jsonb
   WHERE id=1`,
            [mode, JSON.stringify(evidence)],
        );

    it("preserves existing sources, defaults new sources and keeps siblings independent", async () => {
        await seed();
        const baseline = await row();
        expect(baseline).toMatchObject({
            comedy_policy: "unreviewed",
            comedy_gate_mode: "off",
            comedy_policy_version: 1,
        });
        await db.exec(
            "INSERT INTO scraping_sources(id, platform, scraper_key) VALUES (4, 'custom', 'new')",
        );
        expect(await row(4)).toMatchObject({
            comedy_policy: "unreviewed",
            comedy_gate_mode: "off",
            comedy_policy_version: 1,
        });
        await change();
        expect(await row()).toMatchObject({
            id: 1,
            club_id: 10,
            enabled: true,
            comedy_policy: "mixed",
            comedy_gate_mode: "shadow",
            comedy_policy_version: 2,
            comedy_reviewed_by: "operator",
        });
        expect((await row()).comedy_reviewed_at).not.toBeNull();
        expect(await row(2)).toMatchObject({
            id: 2,
            club_id: 10,
            enabled: false,
            comedy_policy: "unreviewed",
            comedy_gate_mode: "off",
        });
        expect(await row(3)).toMatchObject({
            id: 3,
            source_target_id: 20,
            comedy_policy: "unreviewed",
        });
    });

    it("owns revisions, rejects invalid values and auditless changes", async () => {
        await seed();
        await expect(
            db.exec(
                "UPDATE scraping_sources SET comedy_policy='trusted' WHERE id=1",
            ),
        ).rejects.toThrow();
        await expect(
            db.exec(
                "UPDATE scraping_sources SET comedy_gate_mode='disabled' WHERE id=1",
            ),
        ).rejects.toThrow();
        await expect(
            db.exec(
                "UPDATE scraping_sources SET comedy_policy='comedy_only' WHERE id=1",
            ),
        ).rejects.toThrow();
        await expect(
            db.exec(
                "UPDATE scraping_sources SET comedy_reviewed_by='operator', comedy_review_evidence='[]' WHERE id=1",
            ),
        ).rejects.toThrow();
        await db.exec(
            "UPDATE scraping_sources SET comedy_policy_version=99, comedy_reviewed_at=now() WHERE id=1",
        );
        expect(await row()).toMatchObject({
            comedy_policy_version: 1,
            comedy_reviewed_at: null,
        });
        await db.exec(
            "INSERT INTO scraping_sources(id, platform, scraper_key, comedy_policy_version) VALUES (4, 'custom', 'new', 99)",
        );
        expect((await row(4)).comedy_policy_version).toBe(1);
        await change();
        const revised = await row();
        await change();
        expect(await row()).toEqual(revised);
        await db.exec("UPDATE scraping_sources SET enabled=false WHERE id=1");
        expect((await row()).comedy_policy_version).toBe(2);
        await change("enforce");
        expect((await row()).comedy_policy_version).toBe(3);
        await change("enforce", { reason: "additional evidence" });
        expect((await row()).comedy_policy_version).toBe(4);
        await change("off", { reason: "rollback" });
        expect(await row()).toMatchObject({
            id: 1,
            enabled: false,
            comedy_gate_mode: "off",
            comedy_policy_version: 5,
        });
        await db.exec(
            "UPDATE scraping_sources SET comedy_policy='comedy_only' WHERE id=1",
        );
        expect((await row()).comedy_policy_version).toBe(6);
    });

    it("loads the actual venue and aggregate projections before and after migration", async () => {
        await db.exec(`ALTER TABLE scraping_sources
   ADD COLUMN source_url TEXT, ADD COLUMN seatengine_id INTEGER,
   ADD COLUMN seatengine_v3_id TEXT, ADD COLUMN eventbrite_id TEXT,
   ADD COLUMN ticketmaster_id TEXT, ADD COLUMN wix_event_id TEXT,
   ADD COLUMN ovationtix_id TEXT, ADD COLUMN squadup_id TEXT,
   ADD COLUMN metadata JSONB DEFAULT '{}';
   CREATE TABLE source_targets(id INTEGER, name TEXT, slug TEXT, target_type TEXT, source_url TEXT, metadata JSONB);
   CREATE TABLE chain_scraping_defaults(id INTEGER, chain_id INTEGER, scraper_key TEXT, metadata JSONB);
   INSERT INTO source_targets VALUES(20,'Aggregate','aggregate','national',NULL,'{"comedy_policy":"comedy_only"}');
   INSERT INTO chain_scraping_defaults VALUES(1,100,'fallback','{"comedy_policy":"comedy_only"}');
   INSERT INTO scraping_sources(id,club_id,source_target_id,platform,scraper_key,metadata)
    VALUES (1,10,NULL,'custom','venue','{"comedy_policy":"comedy_only"}'),
           (2,NULL,20,'custom','aggregate','{"comedy_gate_mode":"enforce"}');`);
        const queryModule = readFileSync(
            resolve(HERE, "../../scraper/sql/club_queries.py"),
            "utf8",
        );
        const venue = queryModule
            .split('_SCRAPING_SOURCE_JSON = """')[1]
            .split('"""')[0]
            .trim();
        const aggregate = queryModule
            .split('GET_ALL_SOURCE_TARGETS = """')[1]
            .match(/json_build_object\([\s\S]*?\n                    \)/)![0];
        for (const migrated of [false, true]) {
            if (migrated) {
                await db.exec(migration);
                await change();
            }
            for (const [id, projection] of [
                [1, venue],
                [2, aggregate],
            ] as const) {
                const result = await db.query<{
                    source: Record<string, unknown>;
                }>(
                    `SELECT ${projection} AS source
     FROM scraping_sources ss LEFT JOIN source_targets st ON st.id=ss.source_target_id
     LEFT JOIN chain_scraping_defaults csd ON ss.club_id=10 WHERE ss.id=$1`,
                    [id],
                );
                const source = result.rows[0].source;
                expect(source.comedy_policy).toBe(
                    migrated && id === 1 ? "mixed" : "unreviewed",
                );
                expect(source.comedy_gate_mode).toBe(
                    migrated && id === 1 ? "shadow" : "off",
                );
                expect(source.comedy_policy_version).toBe(
                    migrated && id === 1 ? 2 : 1,
                );
            }
        }
    });

    it.runIf(Boolean(process.env.SOURCE_POLICY_SNAPSHOT))(
        "preserves production-shaped source identities and configuration",
        async () => {
            const sources = JSON.parse(
                readFileSync(process.env.SOURCE_POLICY_SNAPSHOT!, "utf8"),
            ) as Record<string, unknown>[];
            expect(sources.length).toBeGreaterThan(0);
            for (const source of sources) {
                await db.query(
                    "INSERT INTO scraping_sources(id,club_id,source_target_id,platform,scraper_key,priority,enabled) VALUES($1,$2,$3,$4,$5,$6,$7)",
                    [
                        source.id,
                        source.club_id,
                        source.source_target_id,
                        source.platform,
                        source.scraper_key,
                        source.priority,
                        source.enabled,
                    ],
                );
            }
            await db.exec(migration);
            const after = await db.query(
                "SELECT id,club_id,source_target_id,platform,scraper_key,priority,enabled FROM scraping_sources ORDER BY id",
            );
            expect(after.rows).toEqual(sources);
            const counts = await db.query<{ count: number }>(
                "SELECT count(*)::int AS count FROM scraping_sources WHERE comedy_policy='unreviewed' AND comedy_gate_mode='off' AND comedy_policy_version=1",
            );
            expect(counts.rows[0].count).toBe(sources.length);
        },
        30000,
    );
});
