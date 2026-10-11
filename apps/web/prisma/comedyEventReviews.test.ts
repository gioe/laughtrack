import { PGlite } from "@electric-sql/pglite";
import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { execFileSync } from "node:child_process";
import { beforeEach, afterEach, it, expect } from "vitest";
const dir = resolve("prisma/migrations");
const migration = (suffix: string) =>
    readFileSync(
        resolve(
            dir,
            readdirSync(dir).find((n) => n.endsWith(suffix))!,
            "migration.sql",
        ),
        "utf8",
    );
const constants = (name: string) =>
    JSON.parse(
        execFileSync(
            "python3",
            [
                "-c",
                `import ast,json,sys
t=ast.parse(open(sys.argv[1]).read());print(json.dumps({n.targets[0].id:ast.literal_eval(n.value) for n in t.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id.endswith('_SQL')}))`,
                resolve(`../scraper/src/laughtrack/core/${name}.py`),
            ],
            { encoding: "utf8" },
        ),
    );
const queries = {
    ...constants("comedy_eligibility_store"),
    ...constants("comedy_eligibility_review_store"),
};
let db: PGlite;
const q = (name: string, args: unknown[] = []) => {
    let i = 0;
    return db.query<Record<string, any>>(
        queries[name].replace(/%s/g, () => `$${++i}`),
        args,
    );
};
beforeEach(async () => {
    db = new PGlite();
    await db.exec(`CREATE TABLE scraping_sources(id INTEGER PRIMARY KEY,enabled BOOLEAN DEFAULT true,
 comedy_policy TEXT DEFAULT 'mixed',comedy_policy_version INTEGER DEFAULT 1,comedy_gate_mode TEXT DEFAULT 'enforce',
 comedy_reviewed_by TEXT,comedy_reviewed_at TIMESTAMPTZ,comedy_review_evidence JSONB DEFAULT '{}',scraper_key TEXT DEFAULT 'test');
 CREATE TABLE clubs(id INTEGER PRIMARY KEY,name TEXT); CREATE TABLE shows(id INTEGER PRIMARY KEY,club_id INTEGER REFERENCES clubs(id));
 INSERT INTO scraping_sources(id) VALUES(1),(2);INSERT INTO clubs VALUES(10,'Harvelles'),(20,'Comedy room');`);
    await db.exec(migration("_add_comedy_eligibility_staging"));
    await db.exec(migration("_add_comedy_event_reviews"));
});
afterEach(async () => {
    await db.close();
});
const stage = async (payload = "a", identity = "identity", source = 1) => {
    const c = (await q("UPSERT_CANDIDATE_SQL", [source, "native:event", 10]))
        .rows[0];
    let d = (
        await q("INSERT_DECISION_SQL", [
            c.id,
            payload,
            identity,
            1,
            "rules",
            "enforce",
            "review",
            JSON.stringify({ name: payload }),
            JSON.stringify({
                reason_codes: ["missing_lineup"],
                lineup_status: "missing",
            }),
        ])
    ).rows[0];
    if (!d)
        d = (
            await q("FIND_DECISION_SQL", [c.id, payload, identity, 1, "rules"])
        ).rows[0];
    await q("INSERT_OBSERVATION_SQL", [
        c.id,
        c.observation_generation,
        d.id,
        identity,
    ]);
    return { c, d };
};
it("reads exact latest observation after dedup reversion and keyset filters", async () => {
    const a = await stage();
    await stage("b");
    const reverted = await stage();
    expect(reverted.d.id).toBe(a.d.id);
    expect((await q("CURRENT_SQL", [a.c.id])).rows[0]).toMatchObject({
        decision_id: a.d.id,
        payload_fingerprint: "a",
    });
    const other = await stage("other", "identity", 2);
    const page = (
        await q("QUEUE_SQL", [
            0,
            other.c.id,
            JSON.stringify({ coverage: "missing", reason: "missing_lineup" }),
            1,
        ])
    ).rows;
    expect(page).toHaveLength(1);
    expect(page[0].candidate_id).toBe(a.c.id);
    expect(
        (
            await q("QUEUE_SQL", [
                a.c.id,
                other.c.id,
                JSON.stringify({ source_id: 2 }),
                2,
            ])
        ).rows,
    ).toHaveLength(1);
    await expect(
        db.exec("UPDATE comedy_event_observations SET generation=99"),
    ).rejects.toThrow();
});
it("retains unknown historical mapping rather than inventing current evidence", async () => {
    const c = (await q("UPSERT_CANDIDATE_SQL", [1, "legacy", 10])).rows[0];
    expect((await q("QUEUE_SQL", [0, c.id, "{}", 10])).rows[0].status).toBe(
        "awaiting_observation",
    );
});
it("records immutable human actions and fences pre-review publication", async () => {
    const { c, d } = await stage();
    await q("INSERT_PREVIEW_SQL", [
        "preview",
        "operator",
        "reject",
        "music",
        JSON.stringify([{ candidate_id: c.id }]),
        "digest",
    ]);
    await q("INSERT_OPERATION_SQL", [
        "op",
        "preview",
        "operator",
        "digest",
        JSON.stringify({ actions: [] }),
    ]);
    expect(
        (await q("ADVANCE_REVIEW_SQL", [c.id, 0, c.observation_generation]))
            .rows[0].review_version,
    ).toBe(1);
    await q("INSERT_REVIEW_SQL", [
        c.id,
        c.observation_generation,
        d.id,
        1,
        "a",
        "identity",
        1,
        "operator",
        "music",
        "reject",
        "op",
    ]);
    expect(
        (await q("LOAD_REVIEW_SQL", [1, "native:event"])).rows[0],
    ).toMatchObject({ action: "reject", review_version: 1 });
    expect(
        (
            await q("VERIFY_CANDIDATE_SQL", [
                c.id,
                1,
                "native:event",
                d.id,
                1,
                c.observation_generation,
                0,
            ])
        ).rows,
    ).toHaveLength(0);
    expect(
        (await q("QUEUE_SQL", [0, c.id, '{"status":"reject"}', 10])).rows,
    ).toHaveLength(1);
    expect(
        (await q("ADVANCE_REVIEW_SQL", [c.id, 0, c.observation_generation]))
            .rows,
    ).toHaveLength(0);
    await expect(
        db.exec("UPDATE comedy_event_reviews SET action='approve'"),
    ).rejects.toThrow();
    await expect(
        db.exec("DELETE FROM comedy_review_operations"),
    ).rejects.toThrow();
    await expect(
        q("INSERT_OPERATION_SQL", ["op", "preview", "other", "digest", "{}"]),
    ).rejects.toThrow();
    await stage("changed");
    expect(
        (await q("QUEUE_SQL", [0, c.id, '{"status":"stale_review"}', 10])).rows,
    ).toHaveLength(1);
});
it("rolls back multi-action changes atomically and refuses cross-candidate decision links", async () => {
    const a = await stage(),
        b = await stage("b", "identity", 2);
    await db.exec("BEGIN");
    await q("ADVANCE_REVIEW_SQL", [a.c.id, 0, a.c.observation_generation]);
    expect(
        (await q("ADVANCE_REVIEW_SQL", [b.c.id, 9, b.c.observation_generation]))
            .rows,
    ).toHaveLength(0);
    await db.exec("ROLLBACK");
    expect((await q("CURRENT_SQL", [a.c.id])).rows[0].review_version).toBe(0);
    await expect(
        q("INSERT_OBSERVATION_SQL", [a.c.id, 99, b.d.id, "bad"]),
    ).rejects.toThrow();
});

it("requires a human action to cite the decision actually observed at that generation", async () => {
    const a = await stage("a");
    const b = await stage("b");
    await q("INSERT_PREVIEW_SQL", [
        "p",
        "operator",
        "approve",
        "reviewed",
        JSON.stringify([{ candidate_id: a.c.id }]),
        "digest",
    ]);
    await q("INSERT_OPERATION_SQL", ["op", "p", "operator", "digest", "{}"]);
    await expect(
        q("INSERT_REVIEW_SQL", [
            a.c.id,
            a.c.observation_generation,
            b.d.id,
            1,
            "b",
            "identity",
            1,
            "operator",
            "reviewed",
            "approve",
            "op",
        ]),
    ).rejects.toThrow();
});
