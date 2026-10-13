import { PGlite } from "@electric-sql/pglite";
import { Prisma } from "@prisma/client";
import { afterAll, beforeAll, beforeEach, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ raw: vi.fn(), transaction: vi.fn() }));
vi.mock("@/lib/db", () => ({
    db: { $queryRaw: mocks.raw, $transaction: mocks.transaction },
}));
import { listReviews, getReview, decideReview } from "./reviews";
let pg: PGlite;
function adapter(conn: Pick<PGlite, "query">) {
    return async (
        arg: Prisma.Sql | TemplateStringsArray,
        ...values: unknown[]
    ) => {
        const sql = Array.isArray(arg)
            ? Prisma.sql(arg as TemplateStringsArray, ...values)
            : (arg as Prisma.Sql);
        return (await conn.query(sql.text, sql.values)).rows;
    };
}
beforeAll(async () => {
    pg = new PGlite();
    await pg.exec(`CREATE TABLE comedians(id serial PRIMARY KEY,name text,visible boolean default true,website text,total_shows int default 0,parent_comedian_id int,block_reason text,block_added_by text,block_added_at timestamptz);
    CREATE TABLE clubs(id serial PRIMARY KEY,name text,visible boolean default true,website text,total_shows int default 0,address text,status text default 'active',club_type text default 'club',closed_at timestamptz);
    CREATE TABLE admin_action_audits(id serial PRIMARY KEY,actor_profile_id text,action text,entity_type text,entity_id text,reason text,before_json jsonb,after_json jsonb,created_at timestamptz default now());
    CREATE TABLE comedian_deny_list(name text);
    CREATE TABLE scraping_sources(id serial PRIMARY KEY,club_id int,enabled boolean);`);
}, 20000);
afterAll(async () => pg?.close());
beforeEach(async () => {
    await pg.exec(`TRUNCATE comedians,clubs,admin_action_audits,comedian_deny_list,scraping_sources RESTART IDENTITY;
    INSERT INTO comedians(id,name,parent_comedian_id) VALUES(1,'Alias Comic',2),(2,'Parent Comic',null);
    INSERT INTO clubs(id,name,address,status) VALUES(1,'Test Club','Main Street','closed');
    INSERT INTO scraping_sources(club_id,enabled) VALUES(1,true);
    INSERT INTO comedian_deny_list(name) VALUES('Alias Comic');`);
    mocks.raw.mockImplementation(adapter(pg));
    mocks.transaction.mockImplementation((fn) =>
        pg.transaction((tx) => fn({ $queryRaw: adapter(tx) })),
    );
});
it.each(["comedian_visibility", "club_visibility"] as const)(
    "lists, blocks and unblocks %s with immutable audit evidence",
    async (workflow) => {
        expect((await listReviews({ workflow, status: "blocked" })).total).toBe(
            0,
        );
        expect(
            (await listReviews({ workflow, q: "' OR 1=1 --" })).items,
        ).toEqual([]);
        const before = (await getReview(workflow, "1"))!;
        expect(before.actions).toEqual(["block"]);
        const decision = {
            workflow,
            id: "1",
            action: "block" as const,
            reason: "Reviewed source evidence",
            token: before.token,
        };
        await decideReview(decision, "admin");
        expect((await listReviews({ workflow, status: "blocked" })).total).toBe(
            1,
        );
        const blocked = (await getReview(workflow, "1"))!;
        expect(blocked.actions).toEqual(["unblock"]);
        expect(blocked.history[0]).toMatchObject({
            actor: "admin",
            reason: "Reviewed source evidence",
        });
        await expect(decideReview(decision, "admin")).rejects.toThrow(
            "changed",
        );
        await decideReview(
            {
                ...decision,
                action: "unblock",
                token: blocked.token,
                reason: "Reviewed restoration",
            },
            "second-admin",
        );
        const restored = (await getReview(workflow, "1"))!;
        expect(restored.status).toBe("active");
        expect(restored.history).toHaveLength(2);
        // An intervening cycle must invalidate the original active snapshot too.
        await expect(decideReview(decision, "admin")).rejects.toThrow(
            "changed",
        );
        expect(
            (await pg.query("SELECT name FROM comedian_deny_list")).rows,
        ).toHaveLength(1);
        expect(
            (await pg.query("SELECT enabled FROM scraping_sources")).rows[0],
        ).toEqual({ enabled: true });
        expect((await pg.query("SELECT status FROM clubs")).rows[0]).toEqual({
            status: "closed",
        });
        expect(
            (
                await pg.query(
                    "SELECT parent_comedian_id FROM comedians WHERE id=1",
                )
            ).rows[0],
        ).toEqual({ parent_comedian_id: 2 });
        const audit = (
            await pg.query(
                "SELECT before_json,after_json FROM admin_action_audits ORDER BY id",
            )
        ).rows as any[];
        expect(audit[0].before_json.visible).toBe(true);
        expect(audit[0].after_json.visible).toBe(false);
        expect(audit[1].before_json.visible).toBe(false);
        expect(audit[1].after_json.visible).toBe(true);
    },
);
it("records comedian block metadata and preserves it on restoration", async () => {
    const before = (await getReview("comedian_visibility", "1"))!;
    expect(before.evidence[1].context).toContain(
        "also on the ingestion deny list",
    );
    await decideReview(
        {
            workflow: "comedian_visibility",
            id: "1",
            action: "block",
            reason: "Not a performer",
            token: before.token,
        },
        "admin",
    );
    const row = (
        await pg.query(
            "SELECT block_reason,block_added_by,block_added_at FROM comedians WHERE id=1",
        )
    ).rows[0] as any;
    expect(row.block_reason).toBe("Not a performer");
    expect(row.block_added_by).toBe("admin");
    expect(row.block_added_at).toBeTruthy();
});
it("rejects missing reasons, invalid actions, invalid IDs and stale edits without an audit write", async () => {
    const before = (await getReview("club_visibility", "1"))!;
    const decision = {
        workflow: "club_visibility" as const,
        id: "1",
        action: "block" as const,
        reason: "Confirmed",
        token: before.token,
    };
    await expect(
        decideReview({ ...decision, reason: " " }, "admin"),
    ).rejects.toThrow();
    await expect(
        decideReview({ ...decision, action: "approve" }, "admin"),
    ).rejects.toThrow("Invalid action");
    await expect(
        decideReview({ ...decision, action: "unblock" }, "admin"),
    ).rejects.toThrow("current visibility");
    await expect(getReview("club_visibility", "-1")).rejects.toThrow(
        "Invalid review item",
    );
    await pg.exec("UPDATE clubs SET name='Changed name' WHERE id=1");
    await expect(decideReview(decision, "admin")).rejects.toThrow("changed");
    expect(
        (await pg.query("SELECT * FROM admin_action_audits")).rows,
    ).toHaveLength(0);
    expect(await getReview("club_visibility", "99")).toBeNull();
});
it("rolls back visibility when audit insertion fails", async () => {
    const before = (await getReview("club_visibility", "1"))!;
    await pg.exec(
        "ALTER TABLE admin_action_audits ADD CONSTRAINT reject_actor CHECK(actor_profile_id <> 'fail')",
    );
    try {
        await expect(
            decideReview(
                {
                    workflow: "club_visibility",
                    id: "1",
                    action: "block",
                    reason: "Confirmed",
                    token: before.token,
                },
                "fail",
            ),
        ).rejects.toThrow();
    } finally {
        await pg.exec(
            "ALTER TABLE admin_action_audits DROP CONSTRAINT reject_actor",
        );
    }
    expect((await getReview("club_visibility", "1"))!.status).toBe("active");
});
