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
            n.endsWith("_add_comedy_model_cache"),
        )!,
        "migration.sql",
    ),
    "utf8",
);
const queries = JSON.parse(
    execFileSync(
        "python3",
        [
            "-c",
            `import ast,json,sys
t=ast.parse(open(sys.argv[1]).read())
print(json.dumps({n.targets[0].id:ast.literal_eval(n.value) for n in t.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id.endswith('_SQL')}))`,
            resolve(
                "../scraper/src/laughtrack/core/comedy_eligibility_model_store.py",
            ),
        ],
        { encoding: "utf8" },
    ),
);
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
    await db.exec(migration);
});
afterEach(async () => {
    await db.close();
});
const reserve = async (
    token: string,
    key: string,
    cost = 60,
    budget = 100,
    limit = 10,
    concurrency = 2,
) => {
    await db.exec("BEGIN");
    await q("LOCK_SQL");
    const rows = (
        await q("RESERVE_SQL", [
            token,
            key,
            cost,
            cost,
            60,
            key,
            key,
            concurrency,
            limit,
            cost,
            budget,
        ])
    ).rows;
    await db.exec("COMMIT");
    return rows;
};
const complete = async (token: string, key: string, cost = 20) => {
    await db.exec("BEGIN");
    await q("LOCK_SQL");
    const rows = (await q("COMPLETE_SQL", [cost, cost, token, cost])).rows;
    if (rows.length)
        await q("CACHE_SQL", [
            key,
            token,
            JSON.stringify({ decision: "accept", model: "fixture" }),
        ]);
    else await q("OVERAGE_SQL", [cost, cost, token]);
    await db.exec("COMMIT");
    return rows;
};
it("serial reservations enforce budget, deduplicate keys, and refund known unused reservation", async () => {
    expect(await reserve("a", "first")).toHaveLength(1);
    expect(await reserve("b", "first", 10)).toHaveLength(0);
    expect(await reserve("c", "second")).toHaveLength(0);
    await complete("a", "first", 20);
    expect((await q("LOOKUP_SQL", ["first"])).rows[0].result.decision).toBe(
        "accept",
    );
    expect(await reserve("d", "first", 10)).toHaveLength(0);
    expect(await reserve("e", "second")).toHaveLength(1);
    expect(
        Number(
            (
                await db.query<{ n: string }>(
                    "SELECT sum(charged_micros) n FROM comedy_model_attempts",
                )
            ).rows[0].n,
        ),
    ).toBe(80);
});
it("charges failures and each retry and caps request count independently", async () => {
    await reserve("a", "first", 20, 100, 2);
    await q("FAIL_SQL", ["a"]);
    expect(await reserve("b", "first", 20, 100, 2)).toHaveLength(1);
    await q("FAIL_SQL", ["b"]);
    expect(await reserve("c", "third", 1, 100, 2)).toHaveLength(0);
    expect(
        Number(
            (
                await db.query<{ n: string }>(
                    "SELECT sum(charged_micros) n FROM comedy_model_attempts",
                )
            ).rows[0].n,
        ),
    ).toBe(40);
});
it("limits active leases and prevents expired owners completing after reassignment", async () => {
    await reserve("old", "first", 20, 100, 10, 1);
    expect(await reserve("b", "second", 20, 100, 10, 1)).toHaveLength(0);
    await db.exec(
        "UPDATE comedy_model_attempts SET lease_until=now()-interval '1 second' WHERE token='old'",
    );
    expect(await reserve("new", "first", 20, 100, 10, 1)).toHaveLength(1);
    expect(await complete("old", "first", 10)).toHaveLength(0);
    expect((await q("LOOKUP_SQL", ["first"])).rows).toHaveLength(0);
    expect(await complete("new", "first", 15)).toHaveLength(1);
    expect(
        (await db.query("SELECT owner_token FROM comedy_model_cache")).rows[0],
    ).toEqual({ owner_token: "new" });
    expect(
        Number(
            (
                await db.query<{ n: string }>(
                    "SELECT sum(charged_micros) n FROM comedy_model_attempts",
                )
            ).rows[0].n,
        ),
    ).toBe(35);
});
it("records provider overages without caching and blocks further spending", async () => {
    await reserve("a", "first", 20, 100);
    expect(await complete("a", "first", 120)).toHaveLength(0);
    expect((await q("LOOKUP_SQL", ["first"])).rows).toHaveLength(0);
    expect(await reserve("b", "second", 1, 100)).toHaveLength(0);
    expect(
        (
            await db.query(
                "SELECT state,charged_micros FROM comedy_model_attempts",
            )
        ).rows[0],
    ).toMatchObject({ state: "failed", charged_micros: 120 });
});

it("charges known malformed-response usage without caching or refunding uncertainty", async () => {
    await reserve("bad", "malformed", 20, 100);
    await db.exec("BEGIN");
    await q("LOCK_SQL");
    await q("OVERAGE_SQL", [120, 120, "bad"]);
    await db.exec("COMMIT");
    expect((await q("LOOKUP_SQL", ["malformed"])).rows).toHaveLength(0);
    expect(
        (
            await db.query(
                "SELECT state,actual_micros,charged_micros FROM comedy_model_attempts WHERE token='bad'",
            )
        ).rows[0],
    ).toMatchObject({
        state: "failed",
        actual_micros: 120,
        charged_micros: 120,
    });
    expect(await reserve("retry", "malformed", 1, 100)).toHaveLength(0);
});
