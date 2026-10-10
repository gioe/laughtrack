import { PGlite } from "@electric-sql/pglite";
import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { execFileSync } from "node:child_process";
import { afterEach, beforeEach, expect, it } from "vitest";

const migrations = resolve("prisma/migrations");
const migration = readFileSync(
    resolve(
        migrations,
        readdirSync(migrations).find((n) =>
            n.endsWith("_add_comedy_eligibility_staging"),
        )!,
        "migration.sql",
    ),
    "utf8",
);
// Exercise the actual Python SQL constants, not a second handwritten implementation.
const source = resolve(
    "../scraper/src/laughtrack/core/comedy_eligibility_store.py",
);
const queries = JSON.parse(
    execFileSync(
        "python3",
        [
            "-c",
            `import ast,json,sys
tree=ast.parse(open(sys.argv[1]).read())
print(json.dumps({n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id.endswith('_SQL')}))`,
            source,
        ],
        { encoding: "utf8" },
    ),
);
let db: PGlite;
const q = (name: string, args: unknown[]) => {
    let i = 0;
    return db.query<Record<string, any>>(
        queries[name].replace(/%s/g, () => `$${++i}`),
        args,
    );
};
beforeEach(async () => {
    db = new PGlite();
    await db.exec(`CREATE TABLE scraping_sources(id INTEGER PRIMARY KEY, enabled BOOLEAN DEFAULT true);
 CREATE TABLE clubs(id INTEGER PRIMARY KEY); CREATE TABLE shows(id INTEGER PRIMARY KEY,club_id INTEGER REFERENCES clubs(id));
 INSERT INTO scraping_sources VALUES(1,true),(2,true); INSERT INTO clubs VALUES(10),(20);
 INSERT INTO shows VALUES(100,10),(200,20);`);
    if (process.env.SOURCE_POLICY_SNAPSHOT) {
        const rows = JSON.parse(
            readFileSync(process.env.SOURCE_POLICY_SNAPSHOT, "utf8"),
        );
        await db.query(
            `INSERT INTO scraping_sources(id,enabled)
            SELECT id,enabled FROM jsonb_to_recordset($1::jsonb) AS x(id INTEGER,enabled BOOLEAN)
            ON CONFLICT(id) DO NOTHING`,
            [JSON.stringify(rows)],
        );
        expect(
            Number(
                (
                    await db.query<{ n: number }>(
                        "SELECT count(*) AS n FROM scraping_sources",
                    )
                ).rows[0].n,
            ),
        ).toBeGreaterThanOrEqual(rows.length);
    }
    await db.exec(migration);
});
afterEach(async () => {
    await db.close();
});
const candidate = async (sourceId = 1) =>
    (await q("UPSERT_CANDIDATE_SQL", [sourceId, "native:event", 10])).rows[0]
        .id;
const decision = async (id: number, identity = "identity-v1") =>
    q("INSERT_DECISION_SQL", [
        id,
        "payload",
        identity,
        1,
        "classifier-v1",
        "enforce",
        "accept",
        JSON.stringify({ title: "Comedy" }),
        JSON.stringify({ decision: "accept" }),
    ]);

it("loads legacy source policy without staging or policy columns", async () => {
    expect((await q("LOAD_SOURCE_SQL", [1])).rows[0]).toMatchObject({
        comedy_policy: "unreviewed",
        comedy_gate_mode: "off",
        comedy_policy_version: 1,
    });
});
it("reuses candidates and revisions while retaining changed identity evidence", async () => {
    const id = await candidate();
    expect(await candidate()).toBe(id);
    const revision = (await decision(id)).rows[0].id;
    expect((await decision(id)).rows).toEqual([]);
    expect(
        (
            await q("FIND_DECISION_SQL", [
                id,
                "payload",
                "identity-v1",
                1,
                "classifier-v1",
            ])
        ).rows[0].id,
    ).toBe(revision);
    expect((await decision(id, "identity-v2")).rows[0].id).not.toBe(revision);
    expect(
        (
            await q("VERIFY_CANDIDATE_SQL", [
                id,
                1,
                "native:event",
                revision,
                1,
                2,
            ])
        ).rows[0],
    ).toMatchObject({ decision: "accept", gate_mode: "enforce" });
    expect(
        (await q("UPSERT_CANDIDATE_SQL", [1, "native:event", 20])).rows,
    ).toEqual([]);
    expect(
        (await db.query("SELECT * FROM comedy_event_decisions")).rows,
    ).toHaveLength(2);
});
it("retains independent source ownership and verifies publication venue", async () => {
    const a = await candidate(),
        b = await candidate(2);
    const da = (await decision(a)).rows[0].id,
        dbb = (await decision(b)).rows[0].id;
    expect((await q("LINK_PUBLICATION_SQL", [a, da, 200])).rows).toEqual([]);
    await q("LINK_PUBLICATION_SQL", [a, da, 100]);
    await q("LINK_PUBLICATION_SQL", [a, da, 100]);
    await q("LINK_PUBLICATION_SQL", [b, dbb, 100]);
    expect(
        (await db.query("SELECT * FROM comedy_event_publications")).rows,
    ).toHaveLength(2);
    await expect(
        db.exec(
            `INSERT INTO comedy_event_publications VALUES (${a},${dbb},100,now())`,
        ),
    ).rejects.toThrow();
    await expect(
        db.exec("DELETE FROM scraping_sources WHERE id=1"),
    ).rejects.toThrow();
    await db.exec("DELETE FROM shows WHERE id=100");
    expect(
        (await db.query("SELECT * FROM comedy_event_decisions")).rows,
    ).toHaveLength(2);
});
it("rejects invalid decision records and rolls back failed staging", async () => {
    const id = await candidate();
    await expect(
        q("INSERT_DECISION_SQL", [
            id,
            "p",
            "i",
            0,
            "v",
            "enforce",
            "accept",
            "{}",
            "{}",
        ]),
    ).rejects.toThrow();
    await expect(
        q("INSERT_DECISION_SQL", [
            id,
            "p",
            "i",
            1,
            "v",
            "enforce",
            "invalid",
            "{}",
            "{}",
        ]),
    ).rejects.toThrow();
    await expect(
        q("INSERT_DECISION_SQL", [
            id,
            "p",
            "i",
            1,
            "v",
            "enforce",
            "review",
            "[]",
            "{}",
        ]),
    ).rejects.toThrow();
    await db.exec("BEGIN");
    await candidate(2);
    await db.exec("ROLLBACK");
    expect(
        (await db.query("SELECT * FROM comedy_event_candidates")).rows,
    ).toHaveLength(1);
});

it("fences older staged decisions while allowing a freshly staged payload reversion", async () => {
    const a = (await q("UPSERT_CANDIDATE_SQL", [1, "native:event", 10]))
        .rows[0];
    const da = (await decision(a.id)).rows[0].id;
    const b = (await q("UPSERT_CANDIDATE_SQL", [1, "native:event", 10]))
        .rows[0];
    const dbb = (
        await q("INSERT_DECISION_SQL", [
            a.id,
            "changed-payload",
            "identity",
            1,
            "classifier-v1",
            "enforce",
            "reject",
            "{}",
            "{}",
        ])
    ).rows[0].id;
    expect(Number(b.observation_generation)).toBe(
        Number(a.observation_generation) + 1,
    );
    expect(
        (
            await q("VERIFY_CANDIDATE_SQL", [
                a.id,
                1,
                "native:event",
                da,
                1,
                a.observation_generation,
            ])
        ).rows,
    ).toEqual([]);
    expect(
        (
            await q("VERIFY_CANDIDATE_SQL", [
                b.id,
                1,
                "native:event",
                dbb,
                1,
                b.observation_generation,
            ])
        ).rows[0].decision,
    ).toBe("reject");
    const c = (await q("UPSERT_CANDIDATE_SQL", [1, "native:event", 10]))
        .rows[0];
    expect((await decision(c.id)).rows).toEqual([]);
    const reused = (
        await q("FIND_DECISION_SQL", [
            c.id,
            "payload",
            "identity-v1",
            1,
            "classifier-v1",
        ])
    ).rows[0].id;
    expect(reused).toBe(da);
    expect(
        (
            await q("VERIFY_CANDIDATE_SQL", [
                c.id,
                1,
                "native:event",
                reused,
                1,
                c.observation_generation,
            ])
        ).rows[0].decision,
    ).toBe("accept");
    expect(
        (
            await q("VERIFY_CANDIDATE_SQL", [
                b.id,
                1,
                "native:event",
                dbb,
                1,
                b.observation_generation,
            ])
        ).rows,
    ).toEqual([]);
});
