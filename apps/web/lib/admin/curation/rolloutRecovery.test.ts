import { PGlite } from "@electric-sql/pglite";
import { readFileSync } from "node:fs";
import { expect, it } from "vitest";

const migrations: string[] = JSON.parse(
    readFileSync("lib/admin/curation/fixtures/migrations.json", "utf8"),
);
const sql = (name: string) =>
    readFileSync(`prisma/migrations/${name}/migration.sql`, "utf8");
const staging = "20261016170000_stage_legacy_relationship_reviews";

it("quarantines legacy links without approving endpoints or losing source rejections", async () => {
    const pg = new PGlite();
    try {
        await pg.exec(
            readFileSync("lib/admin/curation/fixtures/endToEnd.sql", "utf8"),
        );
        // Seed the real pre-enforcement state; subsequent migrations run normally.
        await pg.exec(`
          INSERT INTO comedians(id,uuid,name,parent_comedian_id) VALUES
            (1,'root','Canonical Person',NULL),(2,'child','Legacy Alias',1),(3,'other','Other Person',NULL),(4,'sibling','Sibling Alias',1);
          INSERT INTO podcasts(id,source,source_podcast_id,title) VALUES (1,'feed','p1','Podcast One');
          INSERT INTO comedian_podcasts(id,comedian_id,podcast_id,association_type,source,review_status,evidence) VALUES
            (1,2,1,'host','old-discovery','accepted','{"detail":"unverified"}'),
            (2,3,1,'host','other-source','accepted','{}'),(3,4,1,'host','sibling-source','accepted','{}');
          INSERT INTO podcast_candidate_reviews(id,comedian_id,podcast_id,association_type,source,candidate_status,evidence,reviewed_by) VALUES
            (1,2,1,'host','manual-review','rejected','{"reason":"not a host"}','original-reviewer');
        `);
        for (const name of migrations) await pg.exec(sql(name));
        expect(
            (
                await pg.query(
                    "SELECT parent_comedian_id FROM comedians WHERE id=2",
                )
            ).rows,
        ).toEqual([{ parent_comedian_id: null }]);
        expect(
            (
                await pg.query(
                    "SELECT count(*)::int AS n FROM curation_decisions WHERE action IN ('approve','confirm')",
                )
            ).rows,
        ).toEqual([{ n: 0 }]);
        expect(
            (
                await pg.query(
                    "SELECT disposition FROM curation_relationships WHERE kind='alias_of'",
                )
            ).rows,
        ).toEqual([{ disposition: "proposed" }, { disposition: "proposed" }]);
        expect(
            (
                await pg.query(
                    "SELECT review_status FROM comedian_podcasts ORDER BY id",
                )
            ).rows,
        ).toEqual([
            { review_status: "rejected" },
            { review_status: "pending" },
            { review_status: "rejected" },
        ]);
        expect(
            (
                await pg.query(
                    "SELECT candidate_status,reviewed_by FROM podcast_candidate_reviews",
                )
            ).rows,
        ).toEqual([
            { candidate_status: "rejected", reviewed_by: "original-reviewer" },
        ]);
        expect(
            (
                await pg.query(
                    "SELECT count(*)::int AS n FROM curation_relationships WHERE kind='host_of' AND disposition='rejected'",
                )
            ).rows,
        ).toEqual([{ n: 3 }]);
        expect(
            (
                await pg.query(
                    "SELECT evidence->'legacyRow'->>'review_status' AS state FROM curation_observations WHERE source='legacy-rollout:comedian_podcasts' AND source_key='1'",
                )
            ).rows,
        ).toEqual([{ state: "accepted" }]);
        expect(
            (
                await pg.query(
                    "SELECT tgenabled FROM pg_trigger WHERE tgname='curation_comedian_write'",
                )
            ).rows,
        ).toEqual([{ tgenabled: "O" }]);
        // Both enforcement boundaries are active after the migration, including
        // attempts by old writers to restore the removed live association.
        await expect(
            pg.exec("UPDATE comedians SET parent_comedian_id=1 WHERE id=2"),
        ).rejects.toThrow(/reviewed curation/);
        await pg.exec(
            "UPDATE comedian_podcasts SET review_status='accepted' WHERE id=1",
        );
        expect(
            (
                await pg.query(
                    "SELECT review_status FROM comedian_podcasts WHERE id=1",
                )
            ).rows,
        ).toEqual([{ review_status: "rejected" }]);
        // An already activated installation must retain decisions on replay.
        const before = (
            await pg.query(
                "SELECT count(*)::int AS n FROM curation_observations",
            )
        ).rows;
        await pg.exec(sql(staging));
        expect(
            (
                await pg.query(
                    "SELECT count(*)::int AS n FROM curation_observations",
                )
            ).rows,
        ).toEqual(before);
    } finally {
        await pg.close();
    }
});

it("aborts quarantine atomically for invalid legacy lineage", async () => {
    const pg = new PGlite();
    try {
        await pg.exec(
            readFileSync("lib/admin/curation/fixtures/endToEnd.sql", "utf8"),
        );
        await pg.exec(
            "INSERT INTO comedians(id,uuid,name,parent_comedian_id) VALUES (1,'a','Person A',2),(2,'b','Person B',1)",
        );
        for (const name of migrations.filter((name) => name < staging))
            await pg.exec(sql(name));
        await expect(pg.exec(sql(staging))).rejects.toThrow(
            /cycle or missing endpoint/,
        );
        await pg.exec("ROLLBACK");
        expect(
            (
                await pg.query(
                    "SELECT count(*)::int AS n FROM comedians WHERE parent_comedian_id IS NOT NULL",
                )
            ).rows,
        ).toEqual([{ n: 2 }]);
        expect(
            (
                await pg.query(
                    "SELECT tgenabled FROM pg_trigger WHERE tgname='curation_comedian_write'",
                )
            ).rows,
        ).toEqual([{ tgenabled: "O" }]);
    } finally {
        await pg.close();
    }
});
