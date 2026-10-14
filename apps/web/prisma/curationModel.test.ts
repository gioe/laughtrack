import { PGlite } from "@electric-sql/pglite";
import { readFileSync } from "node:fs";
import { beforeAll, beforeEach, afterAll, it, expect } from "vitest";
import {
    entityTransition,
    relationshipTransition,
    normalizeExactNameV1,
    validateIdentityKey,
} from "../lib/admin/curation/contracts";
let db: PGlite;
beforeAll(async () => {
    db = new PGlite();
    await db.exec(
        `CREATE TABLE comedians(id integer PRIMARY KEY); CREATE TABLE clubs(id integer PRIMARY KEY); CREATE TABLE shows(id integer PRIMARY KEY); CREATE TABLE podcasts(id integer PRIMARY KEY); INSERT INTO comedians VALUES(99);`,
    );
    await db.exec(
        readFileSync(
            "prisma/migrations/20261014010000_durable_curation_model/migration.sql",
            "utf8",
        ),
    );
}, 30000);
afterAll(async () => {
    await db.close();
});
beforeEach(async () => {
    await db.exec("TRUNCATE curation_entities CASCADE");
});
const entity = (id: string, kind = "comedian", scope = "entity") =>
    db.query(
        "INSERT INTO curation_entities(id,kind,label,identity_scope) VALUES($1,$2,$1,$3)",
        [id, kind, scope],
    );
const edge = (id: string, source: string, target: string, kind = "alias_of") =>
    db.query(
        "INSERT INTO curation_relationships(id,kind,source_id,target_id,target_kind) VALUES($1,$2,$3,$4,$5)",
        [
            id,
            kind,
            source,
            target,
            kind === "alias_of" ? "comedian" : "podcast",
        ],
    );
const decide = (
    id: string,
    target: string,
    version: number,
    action: string,
    before: string,
    after: string,
    relationship = false,
) =>
    db.query(
        `INSERT INTO curation_decisions(id,${relationship ? "relationship_id" : "entity_id"},version,action,before_state,after_state,actor,reason) VALUES($1,$2,$3,$4,$5,$6,'admin:1','reviewed evidence')`,
        [id, target, version, action, before, after],
    );
const state = async (id: string) =>
    (
        await db.query(
            "SELECT disposition,version FROM curation_entities WHERE id=$1",
            [id],
        )
    ).rows[0];
it("is additive and validates typed projection bindings", async () => {
    expect(
        (await db.query("SELECT * FROM comedians WHERE id=99")).rows,
    ).toHaveLength(1);
    await entity("c", "club");
    await expect(
        db.exec("UPDATE curation_entities SET comedian_id=99 WHERE id='c'"),
    ).rejects.toThrow();
    await expect(entity("bad", "club", "series")).rejects.toThrow();
});
it("keeps block decisions and keys after projection deletion and rediscovery", async () => {
    await entity("c");
    await db.exec(
        "INSERT INTO comedians VALUES(1); UPDATE curation_entities SET comedian_id=1 WHERE id='c'",
    );
    await db.exec(
        "INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value) VALUES('k','c','comedian','entity','external_id','provider:v1','global','CaseSensitive')",
    );
    await decide("d", "c", 1, "block", "pending", "blocked");
    await db.exec(
        "DELETE FROM comedians WHERE id=1; INSERT INTO comedians VALUES(1)",
    );
    expect(await state("c")).toEqual({ disposition: "blocked", version: 1 });
    expect(
        (
            await db.query(
                "SELECT comedian_id FROM curation_entities WHERE id='c'",
            )
        ).rows[0],
    ).toEqual({ comedian_id: null });
    await entity("new");
    await expect(
        db.exec(
            "INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value) VALUES('k2','new','comedian','entity','external_id','provider:v1','global','CaseSensitive')",
        ),
    ).rejects.toThrow();
    await expect(
        db.exec("DELETE FROM curation_entities WHERE id='c'"),
    ).rejects.toThrow();
    await expect(
        db.exec(
            "UPDATE curation_identity_keys SET entity_id='new' WHERE id='k'",
        ),
    ).rejects.toThrow();
});
it("requires attributed versioned decisions and explicit restoration", async () => {
    await entity("c");
    await expect(
        db.exec(
            "UPDATE curation_entities SET disposition='approved' WHERE id='c'",
        ),
    ).rejects.toThrow();
    await decide("d1", "c", 1, "approve", "pending", "approved");
    await decide("d2", "c", 2, "block", "approved", "blocked");
    await expect(
        decide("bad", "c", 3, "approve", "blocked", "approved"),
    ).rejects.toThrow();
    await decide("d3", "c", 3, "restore", "blocked", "pending");
    await expect(
        decide("stale", "c", 2, "approve", "pending", "approved"),
    ).rejects.toThrow();
    expect(await state("c")).toEqual({ disposition: "pending", version: 3 });
    await expect(db.exec("DELETE FROM curation_decisions")).rejects.toThrow();
    await expect(
        db.exec("UPDATE curation_decisions SET reason='changed'"),
    ).rejects.toThrow();
});
it("a skipped duplicate decision cannot mutate state", async () => {
    await entity("c");
    await decide("d", "c", 1, "block", "pending", "blocked");
    await db.exec(
        "INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason) VALUES('d','c',2,'restore','blocked','pending','admin','retry') ON CONFLICT DO NOTHING",
    );
    expect(await state("c")).toEqual({ disposition: "blocked", version: 1 });
});
it("name and series targets are block-only rules", async () => {
    await entity("name", "comedian", "name");
    await entity("series", "show", "series");
    await expect(
        decide("a", "name", 1, "approve", "pending", "approved"),
    ).rejects.toThrow();
    expect(await state("name")).toEqual({ disposition: "pending", version: 0 });
    expect(
        (await db.query("SELECT * FROM curation_decisions")).rows,
    ).toHaveLength(0);
    await decide("b", "name", 1, "block", "pending", "blocked");
    await decide("s", "series", 1, "block", "pending", "blocked");
    await expect(
        db.exec("UPDATE curation_entities SET comedian_id=99 WHERE id='name'"),
    ).rejects.toThrow();
});
it("observations are append-only and never restore a blocked identity", async () => {
    await entity("c");
    await decide("d", "c", 1, "block", "pending", "blocked");
    await db.exec(
        "INSERT INTO curation_observations(id,entity_id,source,source_key,fingerprint,evidence,observed_at) VALUES('o','c','source','key','hash','{}',now())",
    );
    expect(await state("c")).toEqual({ disposition: "blocked", version: 1 });
    await expect(
        db.exec("DELETE FROM curation_observations"),
    ).rejects.toThrow();
    await expect(
        db.exec(
            "INSERT INTO curation_observations(id,source,source_key,fingerprint,evidence,observed_at) VALUES('bad','source','key','hash','{}',now())",
        ),
    ).rejects.toThrow();
});
it("validates endpoint types, a single active parent, and cycles", async () => {
    for (const id of ["a", "b", "c"]) await entity(id);
    await entity("pod", "podcast");
    await expect(edge("self", "a", "a")).rejects.toThrow();
    await expect(edge("wrong", "a", "pod")).rejects.toThrow();
    await edge("ab", "a", "b");
    await edge("ac", "a", "c");
    await edge("bc", "b", "c");
    await edge("ca", "c", "a");
    await decide("d1", "ab", 1, "confirm", "proposed", "confirmed", true);
    await expect(
        decide("d2", "ac", 1, "confirm", "proposed", "confirmed", true),
    ).rejects.toThrow();
    await decide("d3", "bc", 1, "confirm", "proposed", "confirmed", true);
    await expect(
        decide("d4", "ca", 1, "confirm", "proposed", "confirmed", true),
    ).rejects.toThrow(/cycle/);
    await decide("d5", "ab", 2, "sever", "confirmed", "severed", true);
    await expect(
        decide("d6", "ab", 3, "confirm", "severed", "confirmed", true),
    ).rejects.toThrow();
    await decide("d7", "ca", 1, "confirm", "proposed", "confirmed", true);
    await decide("d8", "ab", 3, "restore", "severed", "proposed", true);
    await expect(
        decide("d9", "ab", 4, "confirm", "proposed", "confirmed", true),
    ).rejects.toThrow(/cycle/);
});
it("allows multiple hosts and retains a source-independent rejected edge", async () => {
    await entity("a");
    await entity("b");
    await entity("p", "podcast");
    await edge("ap", "a", "p", "host_of");
    await edge("bp", "b", "p", "host_of");
    await decide("d1", "ap", 1, "confirm", "proposed", "confirmed", true);
    await decide("d2", "bp", 1, "reject", "proposed", "rejected", true);
    await expect(edge("duplicate", "b", "p", "host_of")).rejects.toThrow();
    await decide("d3", "bp", 2, "restore", "rejected", "proposed", true);
    await decide("d4", "bp", 3, "confirm", "proposed", "confirmed", true);
});
it("keeps processing separate and binds results to the exact immutable request", async () => {
    await entity("c");
    await entity("other");
    await db.exec(
        "INSERT INTO curation_requests(id,entity_id,expected_version,action,actor,reason) VALUES('r','c',0,'block','admin:1','reviewed evidence')",
    );
    expect(await state("c")).toEqual({ disposition: "pending", version: 0 });
    await expect(
        db.exec("UPDATE curation_requests SET action='approve' WHERE id='r'"),
    ).rejects.toThrow();
    await decide("wrong", "other", 1, "block", "pending", "blocked");
    await expect(
        db.exec(
            "UPDATE curation_requests SET status='applied',decision_id='wrong',completed_at=now() WHERE id='r'",
        ),
    ).rejects.toThrow();
    await decide("right", "c", 1, "block", "pending", "blocked");
    await db.exec(
        "UPDATE curation_requests SET status='applied',decision_id='right',completed_at=now() WHERE id='r'",
    );
    await expect(
        db.exec(
            "UPDATE curation_requests SET status='pending',decision_id=NULL,completed_at=NULL WHERE id='r'",
        ),
    ).rejects.toThrow();
    await expect(db.exec("DELETE FROM curation_requests")).rejects.toThrow();
});
it("defines conservative identity normalization and restoration contracts", () => {
    expect(normalizeExactNameV1("  SPEcial\u00a0 Guests!  ")).toBe(
        "special guests!",
    );
    expect(normalizeExactNameV1("Jose\u0301")).toBe("josé");
    expect(normalizeExactNameV1("A-B")).not.toBe(normalizeExactNameV1("A B"));
    expect(() => normalizeExactNameV1("\t ")).toThrow();
    expect(entityTransition("blocked", "restore")).toBe("pending");
    expect(() => entityTransition("blocked", "approve")).toThrow();
    expect(relationshipTransition("severed", "restore")).toBe("proposed");
    expect(() => relationshipTransition("rejected", "confirm")).toThrow();
    expect(() =>
        validateIdentityKey({
            entityKind: "club",
            identityScope: "series",
            keyType: "series_id",
            namespace: "source:v1",
            scope: "global",
            value: "1",
        }),
    ).toThrow();
    expect(() =>
        validateIdentityKey({
            entityKind: "comedian",
            identityScope: "name",
            keyType: "exact_name",
            namespace: "exact-name:v1",
            scope: "global",
            value: "UPPER",
        }),
    ).toThrow();
});
