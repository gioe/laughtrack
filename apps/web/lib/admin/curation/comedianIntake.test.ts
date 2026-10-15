import { PGlite } from "@electric-sql/pglite";
import { readFileSync } from "node:fs";
import { beforeAll, beforeEach, afterAll, it, expect, vi } from "vitest";
import { normalizeExactNameV1 } from "./contracts";
import { Prisma } from "@prisma/client";
const mocks = vi.hoisted(() => ({ raw: vi.fn(), transaction: vi.fn() }));
vi.mock("@/lib/db", () => ({
    db: { $queryRaw: mocks.raw, $transaction: mocks.transaction },
}));
import { decideReview, getReview, undoReview } from "../reviews";
import { createCurationService } from "./decisions";
import { comedianAdapter } from "./comedianAdapter";
let pg: PGlite;
function raw(conn: Pick<PGlite, "query">) {
    return async (
        q: Prisma.Sql | TemplateStringsArray,
        ...values: unknown[]
    ) => {
        const query = Array.isArray(q)
            ? Prisma.sql(q as TemplateStringsArray, ...values)
            : (q as Prisma.Sql);
        return (await conn.query(query.text, query.values)).rows;
    };
}
const migration = readFileSync(
    "prisma/migrations/20261014190000_comedian_curation_intake/migration.sql",
    "utf8",
);
beforeAll(async () => {
    pg = new PGlite();
    await pg.exec(`CREATE TABLE comedians(id serial PRIMARY KEY,uuid text UNIQUE,name text,visible boolean DEFAULT true,parent_comedian_id int,identity_validated_at timestamptz,identity_validated_by text,block_reason text,block_added_by text,block_added_at timestamptz,total_shows int DEFAULT 0,instagram_followers int,bandsintown_id text);
 CREATE TABLE clubs(id int PRIMARY KEY); CREATE TABLE podcasts(id int PRIMARY KEY); CREATE TABLE shows(id int PRIMARY KEY,name text,date timestamptz);
 CREATE TABLE comedian_deny_list(name text PRIMARY KEY);
 CREATE TABLE lineup_items(show_id int,comedian_id text REFERENCES comedians(uuid),UNIQUE(show_id,comedian_id));`);
    await pg.exec(
        readFileSync(
            "prisma/migrations/20261012210000_comedian_identity_review/migration.sql",
            "utf8",
        ),
    );
    await pg.exec(
        readFileSync(
            "prisma/migrations/20261014010000_durable_curation_model/migration.sql",
            "utf8",
        ),
    );
    await pg.exec(migration);
}, 30000);
afterAll(async () => pg.close());
beforeEach(async () => {
    mocks.raw.mockImplementation(raw(pg));
    mocks.transaction.mockImplementation((fn) =>
        pg.transaction((tx) => fn({ $queryRaw: raw(tx) })),
    );
    await pg.exec(
        "TRUNCATE curation_entities,comedians,clubs,podcasts,shows,comedian_deny_list,comedian_identity_candidates CASCADE",
    );
});
async function policy(uuid = "comic", name = "Real Person") {
    return (
        await pg.query<{
            disposition: string;
            entity_id: string;
            comedian_id: number;
        }>("SELECT * FROM curation_comedian_policy($1,$2)", [uuid, name])
    ).rows[0];
}
async function approve(uuid = "comic", name = "Real Person") {
    await pg.query(
        "SELECT curation_approve_comedian($1,$2,'admin','Verified performer')",
        [uuid, name],
    );
    await pg.query(
        "INSERT INTO comedians(uuid,name,identity_validated_at,identity_validated_by) VALUES($1,$2,now(),'admin')",
        [uuid, name],
    );
    return (await policy(uuid, name)).entity_id;
}
async function decide(id: string, action: string) {
    await pg.query(
        `INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason)
 SELECT gen_random_uuid()::text,id,version+1,$2,disposition,CASE $2 WHEN 'block' THEN 'blocked' WHEN 'restore' THEN 'pending' ELSE 'approved' END,'admin','Reviewed' FROM curation_entities WHERE id=$1`,
        [id, action],
    );
}
it("holds every direct insert/upsert until explicit approval, then allows lineup writes", async () => {
    await pg.exec(
        "INSERT INTO comedians(uuid,name) VALUES('comic','Real Person') ON CONFLICT(uuid) DO UPDATE SET name=EXCLUDED.name",
    );
    expect((await pg.query("SELECT * FROM comedians")).rows).toHaveLength(0);
    expect((await policy()).disposition).toBe("pending");
    await approve();
    await pg.exec(
        "INSERT INTO lineup_items VALUES(1,'comic') ON CONFLICT DO NOTHING",
    );
    expect((await pg.query("SELECT * FROM lineup_items")).rows).toHaveLength(1);
});
it("blocks direct, retry, refresh and lineup writes without erasing history", async () => {
    const id = await approve();
    await decide(id, "block");
    await pg.exec(
        "UPDATE comedians SET instagram_followers=999; INSERT INTO lineup_items VALUES(1,'comic'); INSERT INTO comedians(uuid,name) VALUES('retry','REAL  Person') ON CONFLICT(uuid) DO NOTHING",
    );
    expect(
        (await pg.query("SELECT instagram_followers FROM comedians")).rows,
    ).toEqual([{ instagram_followers: null }]);
    expect((await pg.query("SELECT * FROM lineup_items")).rows).toHaveLength(0);
    expect((await pg.query("SELECT * FROM comedians")).rows).toHaveLength(1);
    expect((await policy("retry", "REAL Person")).disposition).toBe("blocked");
    expect(
        (await pg.query("SELECT * FROM curation_observations")).rows.length,
    ).toBeGreaterThan(1);
});
it("exact orphan names and legacy hidden/denied names do not substring-block real people", async () => {
    await pg.exec(
        "INSERT INTO curation_entities(id,kind,identity_scope,label) VALUES('junk','comedian','name','Special Guests!'); INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value) VALUES('junk-key','junk','comedian','name','exact_name','exact-name:v1','global','special guests!')",
    );
    await decide("junk", "block");
    expect((await policy("junk", " SPECIAL\u00a0Guests! ")).disposition).toBe(
        "blocked",
    );
    await approve("real", "Special Guests! Smith");
    await pg.exec("INSERT INTO comedian_deny_list VALUES('Another Person')");
    expect((await policy("other", "another  person")).disposition).toBe(
        "blocked",
    );
    await pg.exec("UPDATE comedians SET visible=false");
    expect((await policy("real", "Special Guests! Smith")).disposition).toBe(
        "blocked",
    );
});
it("rejecting a candidate survives new UUIDs, context and status-reset attempts", async () => {
    await pg.exec(
        "INSERT INTO comedian_identity_candidates(uuid,name) VALUES('candidate','Junk Label'); UPDATE comedian_identity_candidates SET status='rejected',reviewed_by='admin',reason='Not a performer'",
    );
    await pg.exec(
        "UPDATE comedian_identity_candidates SET status='pending'; INSERT INTO comedian_identity_candidates(uuid,name) VALUES('candidate-2','JUNK  LABEL') ON CONFLICT DO NOTHING",
    );
    expect(
        (await pg.query("SELECT status FROM comedian_identity_candidates"))
            .rows,
    ).toEqual([{ status: "rejected" }]);
    await pg.query(
        "SELECT curation_observe_comedian('candidate-2','Junk Label',$1::jsonb)",
        [JSON.stringify({ context: "Changed extraction context" })],
    );
    expect((await policy("candidate-2", "Junk Label")).disposition).toBe(
        "blocked",
    );
    await expect(approve("candidate-2", "Junk Label")).rejects.toThrow(
        /blocked|ambiguous/,
    );
});
it("source IDs and confirmed aliases carry blocks; ambiguous identities never publish", async () => {
    const root = await approve();
    await pg.query(
        "SELECT curation_observe_comedian('comic','Real Person','{}',$1::jsonb)",
        [
            JSON.stringify([
                { namespace: "provider:test:v1", scope: "test", value: "42" },
            ]),
        ],
    );
    await decide(root, "block");
    expect(
        (
            await pg.query<{ disposition: string }>(
                "SELECT * FROM curation_comedian_policy('changed','Renamed',NULL,$1::jsonb)",
                [
                    JSON.stringify([
                        {
                            namespace: "provider:test:v1",
                            scope: "test",
                            value: "42",
                        },
                    ]),
                ],
            )
        ).rows[0].disposition,
    ).toBe("blocked");
    await pg.exec(
        "INSERT INTO curation_entities(id,kind,label) VALUES('alias','comedian','Alias Person'); INSERT INTO curation_relationships(id,kind,source_id,target_id,target_kind) VALUES('edge','alias_of','alias'," +
            "'" +
            root +
            "','comedian')",
    );
    await pg.exec(
        "INSERT INTO curation_decisions(id,relationship_id,version,action,before_state,after_state,actor,reason) VALUES('edge-confirm','edge',1,'confirm','proposed','confirmed','admin','Verified')",
    );
    expect((await policy("alias", "Alias Person")).disposition).toBe("blocked");
    await pg.exec(
        "INSERT INTO curation_entities(id,kind,label) VALUES('a','comedian','Same Name'),('b','comedian','Same Name')",
    );
    await expect(approve("same", "Same Name")).rejects.toThrow(/ambiguous/);
});
it("visibility never restores a durable block; restore returns to pending", async () => {
    const id = await approve();
    await decide(id, "block");
    await pg.exec(
        "UPDATE comedians SET visible=false; UPDATE comedians SET visible=true",
    );
    expect((await policy()).disposition).toBe("blocked");
    await decide(id, "restore");
    expect((await policy()).disposition).toBe("pending");
    await pg.exec("INSERT INTO lineup_items VALUES(1,'comic')");
    expect((await pg.query("SELECT * FROM lineup_items")).rows).toHaveLength(0);
});
it("fails closed when the serialization/policy substrate is unavailable", async () => {
    await approve();
    await pg.exec("DELETE FROM curation_intake_lock");
    await expect(
        pg.exec("INSERT INTO lineup_items VALUES(1,'comic')"),
    ).rejects.toThrow(/unavailable/);
    await pg.exec("INSERT INTO curation_intake_lock(id) VALUES(1)");
});
it("matches the versioned Unicode whitespace/NFC exact-name contract", async () => {
    for (const name of [
        " JOSÉ\u00a0Smith ",
        "Jose\u0301\u2009Smith",
        "A\u001cB",
        "A\u200bB",
        "John O’Neil",
    ]) {
        const result = await pg.query<{ name: string }>(
            "SELECT curation_exact_name($1) name",
            [name],
        );
        expect(result.rows[0].name).toBe(normalizeExactNameV1(name));
    }
});

it("runs real admin approval, rejection and explicit undo through the SQL guard", async () => {
    await pg.exec(
        "INSERT INTO comedian_identity_candidates(uuid,name) VALUES('candidate','New Person')",
    );
    const submit = async (action: "approve" | "reject") =>
        decideReview(
            {
                workflow: "comedian_identity",
                id: "candidate",
                token: (await getReview("comedian_identity", "candidate"))!
                    .token,
                action,
                reason: "Checked performer evidence",
                showIds: [],
            },
            "admin",
        );
    const rejected = await submit("reject");
    expect((await policy("candidate", "New Person")).disposition).toBe(
        "blocked",
    );
    await undoReview(rejected.decisionId!, "admin");
    expect((await policy("candidate", "New Person")).disposition).toBe(
        "pending",
    );
    const approved = await submit("approve");
    expect((await pg.query("SELECT * FROM comedians")).rows).toHaveLength(1);
    expect((await policy("candidate", "New Person")).disposition).toBe(
        "approved",
    );
    await undoReview(approved.decisionId!, "admin");
    expect(
        (await pg.query("SELECT disposition FROM curation_entities")).rows,
    ).toEqual([{ disposition: "pending" }]);
});
it("shared block/restore requests reopen review without erasing other blocks", async () => {
    await pg.exec(
        "INSERT INTO comedian_identity_candidates(uuid,name) VALUES('candidate','New Person')",
    );
    const id = (await policy("candidate", "New Person")).entity_id;
    const service = createCurationService({
        store: {
            $queryRaw: raw(pg),
            $transaction: (fn: (tx: any) => Promise<any>) =>
                pg.transaction((tx) => fn({ $queryRaw: raw(tx) })),
        } as any,
        adapter: () => comedianAdapter,
        invalidate: async () => {},
    });
    const command = {
        requestId: crypto.randomUUID(),
        target: { type: "entity", id, kind: "comedian", scope: "entity" },
        expectedVersion: 0,
        action: "block",
        reason: "Not a performer",
    };
    expect((await service.submit(command, "admin")).status).toBe("applied");
    expect((await policy("candidate", "New Person")).disposition).toBe(
        "blocked",
    );
    expect(
        (
            await service.submit(
                {
                    ...command,
                    requestId: crypto.randomUUID(),
                    expectedVersion: 1,
                    action: "restore",
                },
                "admin",
            )
        ).status,
    ).toBe("applied");
    expect((await policy("candidate", "New Person")).disposition).toBe(
        "pending",
    );
});
it("blocked provider IDs cannot be attached through enrichment", async () => {
    const id = await approve("bad", "Wrong Person");
    await pg.exec("UPDATE comedians SET bandsintown_id='42' WHERE uuid='bad'");
    await decide(id, "block");
    await approve("good", "Good Person");
    await pg.exec("UPDATE comedians SET bandsintown_id='42' WHERE uuid='good'");
    expect(
        (
            await pg.query(
                "SELECT bandsintown_id FROM comedians WHERE uuid='good'",
            )
        ).rows,
    ).toEqual([{ bandsintown_id: null }]);
});

it("does not infer an approved performer from a rejected show-title value", async () => {
    await approve();
    await pg.exec(
        "INSERT INTO comedian_identity_candidates(uuid,name,status,reviewed_by,reason) VALUES('title','Real Person Comedy','rejected','admin','Not a performer'); INSERT INTO shows(id,name) VALUES(10,'Real Person Comedy'); INSERT INTO lineup_items VALUES(10,'comic')",
    );
    expect((await pg.query("SELECT * FROM lineup_items")).rows).toHaveLength(0);
});
