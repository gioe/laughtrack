import { PGlite } from "@electric-sql/pglite";
import { Prisma } from "@prisma/client";
import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { beforeAll, beforeEach, afterAll, expect, it, vi } from "vitest";
import {
    CurationError,
    createCurationService,
    commandSchema,
    type Adapter,
    type Command,
    type SqlClient,
    type Store,
} from "./decisions";
import { resolveEntity, resolveRelationship } from "./resolution";
let pg: PGlite, store: Store, adapter: Adapter, enabled: boolean;
const invalidate = vi.fn(async () => {});
const sql = (conn: Pick<PGlite, "query">): SqlClient => ({
    $queryRaw: async <T>(query: Prisma.Sql) =>
        (await conn.query(query.text, query.values)).rows as T,
});
const service = () =>
    createCurationService({
        store,
        adapter: () => (enabled ? adapter : undefined),
        invalidate,
    });
const command = (
    action: Command["action"] = "approve",
    version = 0,
): Command => ({
    requestId: randomUUID(),
    target: { type: "entity", id: "a", kind: "comedian", scope: "entity" },
    expectedVersion: version,
    action,
    reason: "Reviewed source evidence",
});
const relation = (
    action: Command["action"] = "confirm",
    version = 0,
): Command => ({
    ...command(action, version),
    target: { type: "relationship", id: "edge", kind: "host_of" },
});
const rows = async (table: string) =>
    (await pg.query(`SELECT * FROM ${table}`)).rows;
beforeAll(async () => {
    pg = new PGlite();
    await pg.exec(
        "CREATE TABLE comedians(id integer PRIMARY KEY); CREATE TABLE clubs(id integer PRIMARY KEY); CREATE TABLE shows(id integer PRIMARY KEY); CREATE TABLE podcasts(id integer PRIMARY KEY); CREATE TABLE effects(id text PRIMARY KEY,action text)",
    );
    await pg.exec(
        readFileSync(
            "prisma/migrations/20261014010000_durable_curation_model/migration.sql",
            "utf8",
        ),
    );
    store = {
        ...sql(pg),
        $transaction: (fn) => pg.transaction((tx) => fn(sql(tx))),
    };
}, 30000);
afterAll(async () => pg.close());
beforeEach(async () => {
    await pg.exec(`TRUNCATE curation_entities,effects CASCADE;
 INSERT INTO curation_entities(id,kind,label) VALUES('a','comedian','A'),('b','comedian','B'),('pod','podcast','Podcast');
 INSERT INTO curation_relationships(id,kind,source_id,target_id,target_kind) VALUES('edge','host_of','a','pod','podcast');
 INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value) VALUES('key','a','comedian','entity','external_id','provider:v1','global','123');`);
    enabled = true;
    invalidate.mockClear();
    adapter = {
        mode: "immediate",
        validate: vi.fn(async () => {}),
        preview: vi.fn(async () => ["Update this target projection"]),
        apply: vi.fn(async (tx, _target, _row, c) => {
            await tx.$queryRaw(
                Prisma.sql`INSERT INTO effects(id,action) VALUES(${c.requestId},${c.action}) RETURNING id`,
            );
        }),
    };
});
it("atomically applies the ledger, disposition, effect and attributed receipt", async () => {
    const input = command(),
        result = await service().submit(input, "admin");
    expect(result).toMatchObject({
        status: "applied",
        actor: "admin",
        decision_id: expect.any(String),
    });
    expect((await rows("curation_decisions"))[0]).toMatchObject({
        actor: "admin",
        reason: input.reason,
        version: 1,
    });
    expect(
        (await rows("curation_entities")).find((e: any) => e.id === "a"),
    ).toMatchObject({ disposition: "approved", version: 1 });
    expect(await rows("effects")).toHaveLength(1);
    expect(invalidate).toHaveBeenCalledWith(input.target);
    expect((await rows("curation_relationships"))[0]).toMatchObject({
        disposition: "proposed",
        version: 0,
    });
});
it("replays exact retries without duplicate effects and rejects ID reuse", async () => {
    const c = command();
    const first = await service().submit(c, "admin");
    expect(await service().submit(c, "admin")).toEqual(first);
    expect(await rows("effects")).toHaveLength(1);
    await expect(
        service().submit({ ...c, reason: "Different reason" }, "admin"),
    ).rejects.toMatchObject({ code: "idempotency_conflict" });
    await expect(service().submit(c, "another-admin")).rejects.toMatchObject({
        code: "idempotency_conflict",
    });
});
it("concurrent retries apply once", async () => {
    const c = command();
    const results = await Promise.all([
        service().submit(c, "admin"),
        service().submit(c, "admin"),
    ]);
    expect(results.map((r) => r.status)).toEqual(["applied", "applied"]);
    expect(await rows("effects")).toHaveLength(1);
});
it("stale versions include current state and scope mismatch never writes", async () => {
    await service().submit(command(), "admin");
    await expect(
        service().submit(command("block"), "admin"),
    ).rejects.toMatchObject({
        code: "stale_version",
        current: { version: 1, disposition: "approved" },
    });
    const c = command("block", 1);
    c.target = { type: "entity", id: "a", kind: "comedian", scope: "name" };
    await expect(service().submit(c, "admin")).rejects.toMatchObject({
        code: "target_mismatch",
    });
    expect(await rows("curation_requests")).toHaveLength(1);
});
it("rolls back all decision/domain changes on adapter failure and records failure", async () => {
    adapter.apply = async (tx) => {
        await tx.$queryRaw(
            Prisma.sql`INSERT INTO effects VALUES('partial','approve') RETURNING id`,
        );
        throw new Error("private failure");
    };
    const result = await service().submit(command(), "admin");
    expect(result.status).toBe("failed");
    expect(result.error).not.toContain("private failure");
    expect(await rows("curation_decisions")).toHaveLength(0);
    expect(await rows("effects")).toHaveLength(0);
    expect((await rows("curation_entities"))[0]).toMatchObject({
        disposition: "pending",
        version: 0,
    });
    expect(invalidate).not.toHaveBeenCalled();
    expect(await service().process(result.id)).toEqual(result);
});
it("queued commands are submitted, then revalidated and applied by the worker", async () => {
    adapter.mode = "worker";
    const c = command();
    expect((await service().submit(c, "admin")).status).toBe("pending");
    expect(await rows("curation_decisions")).toHaveLength(0);
    expect(invalidate).not.toHaveBeenCalled();
    expect((await service().process(c.requestId)).status).toBe("applied");
    expect(adapter.validate).toHaveBeenCalledTimes(2);
});
it("worker rejects stale queued approvals after another decision", async () => {
    adapter.mode = "worker";
    const c = command();
    await service().submit(c, "admin");
    adapter.mode = "immediate";
    await service().submit(command("block"), "admin");
    expect((await service().process(c.requestId)).status).toBe("conflict");
    expect(await rows("curation_decisions")).toHaveLength(1);
});
it("worker eligibility failure never appears as applied", async () => {
    adapter.mode = "worker";
    const c = command();
    await service().submit(c, "admin");
    adapter.validate = async () => {
        throw new Error("source disabled");
    };
    expect((await service().process(c.requestId)).status).toBe("failed");
    expect(await rows("effects")).toHaveLength(0);
});
it("disabled adapters expose unavailable previews and cannot submit", async () => {
    enabled = false;
    const c = command();
    expect(await service().preview(c)).toMatchObject({
        available: false,
        effects: [],
        disabledReason: expect.any(String),
    });
    await expect(service().submit(c, "admin")).rejects.toMatchObject({
        code: "adapter_unavailable",
        status: 503,
    });
    expect(await rows("curation_requests")).toHaveLength(0);
});
it("blocking and restoration never mutate unrelated edges or publish implicitly", async () => {
    await service().submit(command("block"), "admin");
    await expect(
        service().submit(command("approve", 1), "admin"),
    ).rejects.toMatchObject({ code: "invalid_transition" });
    const c = command("restore", 1);
    expect(await service().preview(c)).toMatchObject({
        before: "blocked",
        after: "pending",
        restoration: expect.stringContaining("does not approve"),
    });
    await service().submit(c, "admin");
    expect(
        (await rows("curation_entities")).find((e: any) => e.id === "a"),
    ).toMatchObject({ disposition: "pending" });
    expect((await rows("curation_relationships"))[0]).toMatchObject({
        disposition: "proposed",
        version: 0,
    });
});
it("severing an edge leaves endpoints intact and requires restore before reconfirmation", async () => {
    await service().submit(relation(), "admin");
    expect(await service().preview(relation("sever", 1))).toMatchObject({
        boundaries: expect.stringContaining("neither endpoint"),
    });
    await service().submit(relation("sever", 1), "admin");
    expect(await rows("curation_entities")).toHaveLength(3);
    expect(
        (await rows("curation_entities")).every(
            (e: any) => e.disposition === "pending",
        ),
    ).toBe(true);
    await expect(
        service().submit(relation("confirm", 2), "admin"),
    ).rejects.toMatchObject({ code: "invalid_transition" });
});
it("block rules override approved keys and newly arriving observations", async () => {
    await service().submit(command(), "admin");
    const key = {
        entityKind: "comedian" as const,
        identityScope: "entity" as const,
        keyType: "external_id" as const,
        namespace: "provider:v1",
        scope: "global",
        value: "123",
    };
    expect((await resolveEntity(store, [key])).status).toBe("approved");
    await pg.exec(
        "INSERT INTO curation_entities(id,kind,identity_scope,label) VALUES('rule','comedian','name','Special Guests!'); INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value) VALUES('rule-key','rule','comedian','name','exact_name','exact-name:v1','global','special guests!')",
    );
    await service().submit(
        {
            ...command("block"),
            target: {
                type: "entity",
                id: "rule",
                kind: "comedian",
                scope: "name",
            },
        },
        "admin",
    );
    await pg.exec(
        "INSERT INTO curation_observations(id,entity_id,source,source_key,fingerprint,evidence,observed_at) VALUES('new','rule','new-provider','new-key','fresh','{}',now())",
    );
    expect(
        await resolveEntity(store, [
            key,
            {
                entityKind: "comedian",
                identityScope: "name",
                keyType: "exact_name",
                namespace: "exact-name:v1",
                scope: "global",
                value: "special guests!",
            },
        ]),
    ).toEqual({ status: "blocked", entityIds: ["rule"] });
});
it("ambiguous keys stay reviewable and rejected edges override approved endpoints", async () => {
    await service().submit(command(), "admin");
    await service().submit(
        {
            ...command(),
            target: {
                type: "entity",
                id: "pod",
                kind: "podcast",
                scope: "entity",
            },
        },
        "admin",
    );
    await service().submit(relation("reject"), "admin");
    expect(
        (await resolveRelationship(store, "host_of", "a", "pod")).status,
    ).toBe("blocked");
    await pg.exec(
        "INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value) VALUES('key2','b','comedian','entity','external_id','provider:v1','global','456')",
    );
    const keys = ["123", "456"].map((value) => ({
        entityKind: "comedian" as const,
        identityScope: "entity" as const,
        keyType: "external_id" as const,
        namespace: "provider:v1",
        scope: "global",
        value,
    }));
    expect((await resolveEntity(store, keys)).status).toBe("review");
    expect((await resolveEntity(store, [])).status).toBe("review");
});
it("cache failure after commit is recoverable by exact replay", async () => {
    invalidate.mockRejectedValueOnce(
        new Error("cache temporarily unavailable"),
    );
    const c = command();
    await expect(service().submit(c, "admin")).rejects.toThrow("cache");
    expect((await service().getRequest(c.requestId)).status).toBe("applied");
    expect((await service().submit(c, "admin")).status).toBe("applied");
    expect(await rows("effects")).toHaveLength(1);
});
it("requires explicit scope, version, reason and excludes client-supplied attribution", () => {
    const c = command();
    for (const patch of [
        { reason: " " },
        { expectedVersion: -1 },
        { actor: "forged" },
        { target: { type: "entity", id: "a", kind: "comedian" } },
    ])
        expect(() => commandSchema.parse({ ...c, ...patch })).toThrow();
});

it("replays a pending receipt despite subsequently changed eligibility", async () => {
    adapter.mode = "worker";
    const c = command();
    const receipt = await service().submit(c, "admin");
    adapter.validate = async () => {
        throw new Error("source now disabled");
    };
    expect(await service().submit(c, "admin")).toEqual(receipt);
    expect((await service().process(c.requestId)).status).toBe("failed");
});
it("validates action/target compatibility before persisting a request", async () => {
    await expect(service().submit(command("sever"), "admin")).rejects.toThrow();
    await expect(
        service().submit(relation("block"), "admin"),
    ).rejects.toThrow();
    expect(await rows("curation_requests")).toHaveLength(0);
});
it("rejects graph constraint conflicts atomically", async () => {
    await pg.exec(
        "INSERT INTO curation_relationships(id,kind,source_id,target_id,target_kind) VALUES('ab','alias_of','a','b','comedian'),('ba','alias_of','b','a','comedian')",
    );
    const c = {
        ...command("confirm"),
        target: {
            type: "relationship" as const,
            id: "ab",
            kind: "alias_of" as const,
        },
    };
    expect((await service().submit(c, "admin")).status).toBe("applied");
    const result = await service().submit(
        { ...c, requestId: randomUUID(), target: { ...c.target, id: "ba" } },
        "admin",
    );
    expect(result.status).toBe("conflict");
    expect(await rows("curation_decisions")).toHaveLength(1);
    expect(await rows("effects")).toHaveLength(1);
});

it("missing source evidence terminates a queued request instead of stranding it", async () => {
    adapter.mode = "worker";
    const c = command();
    await service().submit(c, "admin");
    adapter.validate = async () => {
        throw new CurationError(
            "not_found",
            "Source evidence was removed.",
            404,
        );
    };
    expect((await service().process(c.requestId)).status).toBe("failed");
    expect(await rows("curation_decisions")).toHaveLength(0);
    await expect(service().process(randomUUID())).rejects.toMatchObject({
        code: "not_found",
        status: 404,
    });
});
