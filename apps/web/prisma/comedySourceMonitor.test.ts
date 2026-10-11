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
const constants = (file: string) =>
    JSON.parse(
        execFileSync(
            "python3",
            [
                "-c",
                `import ast,json,sys
t=ast.parse(open(sys.argv[1]).read());print(json.dumps({n.targets[0].id:ast.literal_eval(n.value) for n in t.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id.endswith('_SQL')}))`,
                resolve(`../scraper/src/laughtrack/core/${file}.py`),
            ],
            { encoding: "utf8" },
        ),
    );
const queries = {
    ...constants("comedy_eligibility_monitor_store"),
    ...constants("entities/club/comedy_policy"),
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
    await db.exec(
        "CREATE TABLE scraping_sources(id INTEGER PRIMARY KEY,enabled BOOLEAN DEFAULT true); INSERT INTO scraping_sources VALUES(1,true),(2,false)",
    );
    await db.exec(migration("_add_source_comedy_policies"));
    await db.exec(migration("_add_comedy_source_monitor"));
});
afterEach(async () => {
    await db.close();
});
const sample = (event = "one", version = 1, payload = "payload") =>
    q("RECORD_SAMPLE_SQL", [
        event,
        payload,
        "identity",
        JSON.stringify({ decision: "reject", performers: [] }),
        version,
        1,
        version,
    ]);
const report = async (digest = "digest", evidence = "content") =>
    (
        await q("INSERT_REPORT_SQL", [
            1,
            digest,
            evidence,
            "{}",
            JSON.stringify({ event_count: 20 }),
            JSON.stringify({ downgrade: true }),
            "{}",
        ])
    ).rows;
it("updates freshness without multiplying repeated source/event samples and rejects stale policy versions", async () => {
    await sample();
    await sample();
    await sample("two");
    expect((await q("SAMPLES_SQL", [1, 30])).rows).toHaveLength(2);
    await sample("one", 1, "changed");
    expect((await q("SAMPLES_SQL", [1, 30])).rows[0].payload_fingerprint).toBe(
        "changed",
    );
    expect((await sample("stale", 99)).rows).toHaveLength(0);
    await db.exec(
        "UPDATE comedy_source_samples SET last_seen_at=now()-interval '31 days' WHERE event_key='two'",
    );
    expect((await q("SAMPLES_SQL", [1, 30])).rows).toHaveLength(1);
});
it("deduplicates substantive reports and makes report/transition evidence immutable", async () => {
    const id = (await report())[0].id;
    expect(await report()).toHaveLength(0);
    expect((await q("FIND_REPORT_SQL", [1, "digest"])).rows[0].id).toBe(id);
    expect(await report("changed")).toHaveLength(1);
    await expect(
        db.exec("UPDATE comedy_source_reports SET metrics='{}'"),
    ).rejects.toThrow();
    await q("INSERT_TRANSITION_SQL", [
        1,
        id,
        "downgrade",
        null,
        "monitor",
        "threshold",
        JSON.stringify({ version: 1 }),
        JSON.stringify({ version: 2 }),
    ]);
    await expect(
        db.exec("DELETE FROM comedy_source_transitions"),
    ).rejects.toThrow();
    await expect(
        q("INSERT_TRANSITION_SQL", [
            1,
            id,
            "downgrade",
            null,
            "monitor",
            "threshold",
            "{}",
            "{}",
        ]),
    ).rejects.toThrow();
});
it("policy CAS and rollback preserve accounting and suppress unchanged evidence across config revisions", async () => {
    const trusted = (
        await q("UPDATE_POLICY_SQL", [
            "comedy_only",
            "off",
            "operator",
            '{"reason":"reviewed"}',
            1,
            1,
        ])
    ).rows[0];
    expect(trusted.comedy_policy_version).toBe(2);
    const id = (await report())[0].id;
    const changed = (
        await q("UPDATE_POLICY_SQL", [
            "mixed",
            "enforce",
            "monitor",
            '{"reason":"threshold"}',
            1,
            2,
        ])
    ).rows[0];
    expect(changed.comedy_policy_version).toBe(3);
    expect(
        (
            await q("UPDATE_POLICY_SQL", [
                "comedy_only",
                "off",
                "operator",
                '{"reason":"stale rollback"}',
                1,
                2,
            ])
        ).rows,
    ).toHaveLength(0);
    const down = (
        await q("INSERT_TRANSITION_SQL", [
            1,
            id,
            "downgrade",
            null,
            "monitor",
            "threshold",
            JSON.stringify({
                version: 2,
                policy: "comedy_only",
                gate_mode: "off",
            }),
            JSON.stringify({
                version: 3,
                policy: "mixed",
                gate_mode: "enforce",
            }),
        ])
    ).rows[0];
    await q("UPDATE_POLICY_SQL", [
        "comedy_only",
        "off",
        "operator",
        '{"reason":"rollback"}',
        1,
        3,
    ]);
    await q("INSERT_TRANSITION_SQL", [
        1,
        id,
        "rollback",
        down.id,
        "operator",
        "reviewed rollback",
        JSON.stringify({ version: 3 }),
        JSON.stringify({ version: 4 }),
    ]);
    expect((await q("SUPPRESSED_SQL", [1, "content"])).rows[0].suppressed).toBe(
        true,
    );
    expect(
        (await q("SUPPRESSED_SQL", [1, "different content"])).rows[0]
            .suppressed,
    ).toBe(false);
    await report("newconfig", "content");
    expect((await q("SUPPRESSED_SQL", [1, "content"])).rows[0].suppressed).toBe(
        true,
    );
    expect(
        (
            await db.query(
                "SELECT enabled,comedy_policy_version FROM scraping_sources WHERE id=1",
            )
        ).rows[0],
    ).toMatchObject({ enabled: true, comedy_policy_version: 4 });
});

it("uses exact bounded rolling windows", async () => {
    await sample("inside");
    await sample("future");
    await db.exec(
        "UPDATE comedy_source_samples SET last_seen_at='2026-10-10T12:00:00Z' WHERE event_key='inside'; UPDATE comedy_source_samples SET last_seen_at='2026-10-11T12:00:00Z' WHERE event_key='future'",
    );
    expect(
        (
            await q("SAMPLES_AT_SQL", [
                1,
                "2026-10-10T13:00:00Z",
                "2026-10-10T13:00:00Z",
                30,
            ])
        ).rows.map((r) => r.event_key),
    ).toEqual(["inside"]);
});
