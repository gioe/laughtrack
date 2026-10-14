import { PGlite } from "@electric-sql/pglite";
import { Prisma } from "@prisma/client";
import { readFileSync } from "node:fs";
import { beforeAll, beforeEach, afterAll, it, expect } from "vitest";
import {
    planMigration,
    applyMigration,
    inspectMigration,
    sources,
    type Source,
} from "./migration";
import {
    migrationCompatibility,
    restoreImportedDecision,
} from "./migrationCompatibility";
import type { Store, SqlClient } from "./decisions";
let pg: PGlite, store: Store;
const adapter = (conn: Pick<PGlite, "query">): SqlClient => ({
    $queryRaw: async <T>(q: Prisma.Sql) =>
        (await conn.query(q.text, q.values)).rows as T,
});
beforeAll(async () => {
    pg = new PGlite();
    await pg.exec(`CREATE TABLE comedians(id int PRIMARY KEY,uuid text,name text,visible boolean DEFAULT true,parent_comedian_id int,identity_validated_at timestamptz,identity_validated_by text,block_reason text,block_added_by text,block_added_at timestamptz);
 CREATE TABLE clubs(id int PRIMARY KEY,name text,visible boolean DEFAULT true,google_place_id text);
 CREATE TABLE shows(id int PRIMARY KEY,name text);
 CREATE TABLE podcasts(id int PRIMARY KEY,title text,source text,source_podcast_id text,feed_url text);
 CREATE TABLE comedian_deny_list(name text PRIMARY KEY,reason text,added_by text,deleted_at timestamptz);
 CREATE TABLE venue_deny_list(google_place_id text PRIMARY KEY,name text,reason text,added_by text,denied_at timestamptz,evidence jsonb);
 CREATE TABLE podcast_deny_list(id int PRIMARY KEY,podcast_id int,source text,source_podcast_id text,feed_url text,reason text,denied_by text,denied_at timestamptz,restored_at timestamptz,restored_by text);
 CREATE TABLE comedian_identity_candidates(uuid text PRIMARY KEY,name text,status text,version int,canonical_comedian_id int,reviewed_by text,reviewed_at timestamptz,reason text);
 CREATE TABLE comedian_identity_evidence(fingerprint text PRIMARY KEY,candidate_uuid text,source_url text,context text);
 CREATE TABLE comedian_podcasts(id int PRIMARY KEY,comedian_id int,podcast_id int,source text,association_type text,review_status text,reviewed_by text,reviewed_at timestamptz,evidence jsonb);
 CREATE TABLE podcast_candidate_reviews(id int PRIMARY KEY,comedian_id int,podcast_id int,source text,source_podcast_id text,association_type text,candidate_status text,reviewed_by text,reviewed_at timestamptz,evidence jsonb);
 CREATE TABLE comedy_event_candidates(id int PRIMARY KEY,source_id int,event_key text);
 CREATE TABLE comedy_event_decisions(id int PRIMARY KEY,candidate_id int,payload jsonb);
 CREATE TABLE comedy_event_observations(candidate_id int,generation bigint,decision_id int,baseline_identity_fingerprint text);
 CREATE TABLE comedy_event_publications(candidate_id int,decision_id int,show_id int);
 CREATE TABLE comedy_event_reviews(id int PRIMARY KEY,candidate_id int,decision_id int,action text,actor text,reason text,payload_fingerprint text,identity_fingerprint text,policy_version int,observation_generation bigint,created_at timestamptz);
 CREATE TABLE admin_action_audits(id int PRIMARY KEY,entity_type text,entity_id text,actor_profile_id text,action text,before_json jsonb,after_json jsonb,reason text,created_at timestamptz);
 CREATE TABLE admin_review_decisions(id text PRIMARY KEY,workflow text,item_id text,actor text,action text,reason text,after_json jsonb,before_json jsonb,created_at timestamptz,undone_at timestamptz);`);
    await pg.exec(
        readFileSync(
            "prisma/migrations/20261014010000_durable_curation_model/migration.sql",
            "utf8",
        ),
    );
    store = {
        ...adapter(pg),
        $transaction: (fn) => pg.transaction((tx) => fn(adapter(tx))),
    };
}, 30000);
afterAll(async () => pg.close());
beforeEach(async () => {
    await pg.exec(`TRUNCATE curation_entities,comedians,clubs,shows,podcasts,comedian_deny_list,venue_deny_list,podcast_deny_list,comedian_identity_candidates,comedian_identity_evidence,comedian_podcasts,podcast_candidate_reviews,comedy_event_candidates,comedy_event_decisions,comedy_event_reviews,comedy_event_observations,comedy_event_publications,admin_review_decisions,admin_action_audits CASCADE;
 INSERT INTO comedians(id,uuid,name,visible) VALUES(1,'uuid-1','Real Person',true),(2,'uuid-2','Hidden Person',false),(3,'uuid-3','Alias Person',true);
 UPDATE comedians SET block_reason='Not a performer',block_added_by='admin-old',block_added_at='2026-01-01' WHERE id=2;
 UPDATE comedians SET parent_comedian_id=1 WHERE id=3;
 INSERT INTO clubs VALUES(1,'Organizer proxy',false,'place-1');
 INSERT INTO podcasts VALUES(1,'Podcast','apple','123','https://feed.test/rss');`);
});
const plan = (source: Source, extra = {}) =>
    planMigration(store, { source, environment: "test", limit: 50, ...extra });
const apply = async (source: Source) =>
    applyMigration(store, await plan(source), "operator");
const rows = async (table: string) =>
    (await pg.query<Record<string, any>>(`SELECT * FROM ${table}`)).rows;
async function domainId(kind: string, id: number) {
    return (
        await pg.query<{ id: string }>(
            `SELECT id FROM curation_entities WHERE ${kind}_id=$1`,
            [id],
        )
    ).rows[0].id;
}
it("dry-run inventories all categories without writes, and bounds cursor pages", async () => {
    for (const source of sources) {
        const p = await plan(source);
        expect(p.digest).toHaveLength(64);
        expect((await inspectMigration(store, p)).scanned).toBe(p.items.length);
    }
    expect(await rows("curation_entities")).toHaveLength(0);
    const p = await plan("comedians", { limit: 1 });
    expect(p.items.map((i) => i.key)).toEqual(["1"]);
    expect(p.nextCursor).toBe("1");
    expect(
        (await plan("comedians", { limit: 1, after: p.nextCursor })).items[0]
            .key,
    ).toBe("2");
    await expect(plan("comedians", { limit: 51 })).rejects.toThrow();
});
it("imports hidden comedian/name suppression with attribution, not visible approvals", async () => {
    const before = await rows("comedians");
    const result = await apply("comedians");
    expect(result.held).toBe(0);
    const entities = await rows("curation_entities");
    expect(entities.filter((e) => e.disposition === "blocked")).toHaveLength(2);
    expect(entities.some((e) => e.disposition === "approved")).toBe(false);
    const decisions = await rows("curation_decisions");
    expect(decisions[0]).toMatchObject({
        actor: "admin-old",
        reason: "Not a performer",
        action: "block",
    });
    expect(new Date(decisions[0].created_at).toISOString()).toBe(
        new Date(before.find((r) => r.id === 2)!.block_added_at).toISOString(),
    );
    expect((await rows("curation_relationships"))[0]).toMatchObject({
        kind: "alias_of",
        disposition: "proposed",
    });
    expect(await rows("comedians")).toEqual(before);
    expect((await apply("comedians")).skipped).toBe(3);
    expect(await rows("curation_decisions")).toHaveLength(2);
});
it("preserves name-only denials after the public record was deleted", async () => {
    await pg.exec(
        "INSERT INTO comedian_deny_list VALUES(' Special  Guests! ','placeholder','audit_script','2026-01-01')",
    );
    expect((await apply("comedian_deny_list")).imported).toBe(1);
    expect((await rows("curation_entities"))[0]).toMatchObject({
        kind: "comedian",
        identity_scope: "name",
        disposition: "blocked",
        comedian_id: null,
    });
    expect((await rows("curation_identity_keys"))[0]).toMatchObject({
        namespace: "exact-name:v1",
        value: "special guests!",
    });
});
it("does not reinterpret hidden organizer proxies as denials", async () => {
    await apply("clubs");
    expect((await rows("curation_entities"))[0].disposition).toBe("pending");
    const id = await domainId("club", 1);
    expect((await migrationCompatibility(store, id)).blocked).toBe(false);
    await pg.exec(
        "INSERT INTO venue_deny_list VALUES('place-1','Organizer proxy','Not comedy','triage','2026-01-01','{}')",
    );
    await apply("venue_deny_list");
    expect((await migrationCompatibility(store, id)).blocked).toBe(true);
    expect((await rows("curation_entities"))[0].disposition).toBe("blocked");
});
it("retains podcast denial/restoration history without approval", async () => {
    await pg.exec(
        "INSERT INTO podcast_deny_list VALUES(1,1,'apple','123','https://feed.test/rss','No host','old-admin','2026-01-01','2026-02-01','restorer')",
    );
    expect((await apply("podcast_deny_list")).imported).toBe(1);
    expect((await rows("curation_entities"))[0]).toMatchObject({
        disposition: "pending",
        version: 2,
        podcast_id: 1,
    });
    expect(
        (await rows("curation_decisions")).map((d) => [d.action, d.actor]),
    ).toEqual([
        ["block", "old-admin"],
        ["restore", "restorer"],
    ]);
    expect((await rows("podcast_deny_list"))[0].restored_by).toBe("restorer");
});
it("holds ambiguous place/podcast mappings atomically and reports conflicts", async () => {
    await pg.exec(
        "INSERT INTO clubs VALUES(2,'Duplicate',true,'place-1'); INSERT INTO venue_deny_list VALUES('place-1','Venue','Denied','admin','2026-01-01','{}'); INSERT INTO podcasts VALUES(2,'Other','spotify','x','https://feed.test/rss'); INSERT INTO podcast_deny_list VALUES(1,1,'apple','123','https://feed.test/rss','Denied','admin','2026-01-01',NULL,NULL)",
    );
    for (const source of ["venue_deny_list", "podcast_deny_list"] as Source[]) {
        expect((await inspectMigration(store, await plan(source))).held).toBe(
            1,
        );
        expect((await apply(source)).held).toBe(1);
    }
    expect(await rows("curation_entities")).toHaveLength(0);
});
it("rejects a stale snapshot before importing any rows", async () => {
    const p = await plan("comedians");
    await pg.exec("UPDATE comedians SET visible=false WHERE id=1");
    await expect(applyMigration(store, p, "operator")).rejects.toThrow(
        "snapshot changed",
    );
    expect(await rows("curation_entities")).toHaveLength(0);
});
it("preserves scoped event rejection as evidence only", async () => {
    await pg.exec(
        `INSERT INTO comedy_event_candidates VALUES(1,7,'provider-occurrence'); INSERT INTO comedy_event_decisions VALUES(1,1,'{"name":"Concert"}'); INSERT INTO comedy_event_reviews VALUES(1,1,1,'reject','admin','Music','payload','identity',5,9,'2026-01-01')`,
    );
    expect((await apply("comedy_event_reviews")).imported).toBe(1);
    expect((await rows("curation_entities"))[0]).toMatchObject({
        kind: "show",
        identity_scope: "entity",
        disposition: "pending",
    });
    expect(await rows("curation_decisions")).toHaveLength(0);
    expect((await rows("curation_observations"))[0].evidence.raw).toMatchObject(
        {
            action: "reject",
            policy_version: 5,
            observation_generation: 9,
            payload_fingerprint: "payload",
        },
    );
});
it("accepted automated links remain proposals; rejected source links stay rejected", async () => {
    await pg.exec(
        `INSERT INTO comedian_podcasts VALUES(1,1,1,'automated','host','accepted',NULL,NULL,'{}'),(2,3,1,'manual','host','rejected','admin','2026-01-01','{"reason":"not host"}')`,
    );
    expect((await apply("comedian_podcasts")).held).toBe(0);
    expect(
        (await rows("curation_relationships")).map((r) => r.disposition).sort(),
    ).toEqual(["proposed", "rejected"]);
    expect((await rows("curation_decisions"))[0]).toMatchObject({
        action: "reject",
        actor: "admin",
    });
});
it("conflicting source-specific relationship decisions are held, not widened", async () => {
    await pg.exec(
        "INSERT INTO comedian_podcasts VALUES(1,1,1,'one','host','accepted',NULL,NULL,'{}'),(2,1,1,'two','host','rejected','admin','2026-01-01','{}')",
    );
    expect((await apply("comedian_podcasts")).held).toBe(2);
    expect(await rows("curation_relationships")).toHaveLength(0);
});
it("retains unmaterialized rejected podcast candidates and identity evidence", async () => {
    await pg.exec(
        "INSERT INTO podcast_candidate_reviews VALUES(1,1,NULL,'spotify','new','host','rejected','admin','2026-01-01','{}'); INSERT INTO comedian_identity_candidates VALUES('candidate','Name','rejected',1,NULL,'admin','2026-01-01','Title'); INSERT INTO comedian_identity_evidence VALUES('fingerprint','candidate','https://source.test','raw extraction')",
    );
    expect((await apply("podcast_candidate_reviews")).held).toBe(0);
    expect((await rows("curation_relationships"))[0].disposition).toBe(
        "rejected",
    );
    await apply("comedian_identity_candidates");
    expect(
        (await rows("curation_observations")).find(
            (o) => o.source_key === "comedian_identity_candidates:candidate",
        )!.evidence.context.evidence[0].context,
    ).toBe("raw extraction");
});
it("respects newer manual decisions and keeps legacy suppression effective", async () => {
    await apply("comedians");
    const id = await domainId("comedian", 1);
    await pg.query(
        "INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason) VALUES('manual',$1,1,'approve','pending','approved','reviewer','verified')",
        [id],
    );
    await pg.exec("UPDATE comedians SET visible=false WHERE id=1");
    const result = await apply("comedians");
    expect(result.items.find((i) => i.key === "1")?.status).toBe("held");
    expect((await migrationCompatibility(store, id)).legacyBlocked).toBe(true);
    expect(
        (
            await pg.query(
                "SELECT disposition FROM curation_entities WHERE id=$1",
                [id],
            )
        ).rows[0],
    ).toEqual({ disposition: "approved" });
});
it("restoration requires legacy suppression resolved and restores only review state", async () => {
    await pg.exec(
        "INSERT INTO podcast_deny_list VALUES(1,1,'apple','123','https://feed.test/rss','No host','admin','2026-01-01',NULL,NULL)",
    );
    await apply("podcast_deny_list");
    const id = await domainId("podcast", 1);
    const input = {
        id,
        expectedVersion: 1,
        actor: "operator",
        reason: "Reviewed restored legacy denial",
    };
    await expect(restoreImportedDecision(store, input)).rejects.toThrow(
        "legacy suppression",
    );
    await pg.exec(
        "UPDATE podcast_deny_list SET restored_at='2026-02-01',restored_by='admin' WHERE id=1",
    );
    expect((await apply("podcast_deny_list")).held).toBe(1);
    expect((await restoreImportedDecision(store, input)).disposition).toBe(
        "pending",
    );
    expect((await migrationCompatibility(store, id)).blocked).toBe(false);
    await expect(restoreImportedDecision(store, input)).rejects.toThrow(
        "changed",
    );
    expect((await rows("curation_decisions"))[1]).toMatchObject({
        action: "restore",
        actor: "operator",
    });
});
it("a normalized key collision with another identity is held without partial writes", async () => {
    await apply("clubs");
    const id = await domainId("club", 1);
    await pg.exec(
        "INSERT INTO curation_entities(id,kind,label) VALUES('other','club','Other')",
    );
    await pg.query(
        "INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value) VALUES('conflict','other','club','entity','legacy_id','legacy:test:venue_deny_list:v1','global','x')",
    );
    // A different public record claiming an already owned place ID must not silently rebind it.
    await pg.exec("INSERT INTO clubs VALUES(2,'Second',true,'place-1')");
    const result = await apply("clubs");
    expect(result.items.find((i) => i.key === "2")?.status).toBe("held");
    expect(await domainId("club", 1)).toBe(id);
    expect(
        (await pg.query("SELECT id FROM curation_entities WHERE club_id=2"))
            .rows,
    ).toHaveLength(0);
});

it("imports only current matching admin approvals and preserves older audit history", async () => {
    await pg.exec(`INSERT INTO comedian_identity_candidates VALUES('approved','Real Person','accepted',1,1,'human','2026-01-01','Reviewed');
 INSERT INTO comedian_podcasts VALUES(1,1,1,'source','host','accepted','human','2026-01-01','{}');
 INSERT INTO admin_review_decisions(id,workflow,item_id,actor,action,reason,after_json,created_at)
 SELECT 'identity-audit','comedian_identity','approved','human','approve','Identity evidence',jsonb_build_object('row',to_jsonb(c)),'2026-01-01' FROM comedian_identity_candidates c;
 INSERT INTO admin_review_decisions(id,workflow,item_id,actor,action,reason,after_json,created_at)
 SELECT 'host-audit','podcast_association','1','human','approve','Host evidence',jsonb_build_object('row',to_jsonb(c)),'2026-01-01' FROM comedian_podcasts c;
 INSERT INTO admin_action_audits VALUES(1,'podcast','1','older-admin','podcast_hostship_review.restore','{}','{}',NULL,'2026-01-01');`);
    expect((await apply("comedian_identity_candidates")).held).toBe(0);
    expect(
        (
            await pg.query(
                "SELECT disposition FROM curation_entities WHERE comedian_id=1",
            )
        ).rows[0],
    ).toEqual({ disposition: "approved" });
    expect((await apply("comedian_podcasts")).held).toBe(0);
    expect((await rows("curation_relationships"))[0].disposition).toBe(
        "confirmed",
    );
    expect(
        (await rows("curation_observations")).some((o) =>
            o.evidence.context.domainAudits.some(
                (a: any) => a.action === "podcast_hostship_review.restore",
            ),
        ),
    ).toBe(true);
});
it("stale or undone approvals cannot validate a subsequently changed link", async () => {
    await pg.exec(`INSERT INTO comedian_podcasts VALUES(1,1,1,'source','host','accepted','human','2026-01-01','{}');
 INSERT INTO admin_review_decisions(id,workflow,item_id,actor,action,reason,after_json,created_at)
 SELECT 'old','podcast_association','1','human','approve','Reviewed',jsonb_build_object('row',to_jsonb(c)),'2026-01-01' FROM comedian_podcasts c;
 UPDATE comedian_podcasts SET reviewed_by='automated',reviewed_at='2026-02-01';`);
    await apply("comedian_podcasts");
    expect((await rows("curation_relationships"))[0].disposition).toBe(
        "proposed",
    );
});
it("held rows do not prevent later page records from importing", async () => {
    await pg.exec(
        "INSERT INTO clubs VALUES(2,'Duplicate A',true,'same'),(3,'Duplicate B',true,'same'),(4,'Fine',true,'other')",
    );
    const p = await plan("clubs");
    const report = await applyMigration(store, p, "operator");
    expect(report.imported).toBe(2);
    expect(report.held).toBe(2);
    expect((await inspectMigration(store, p)).alreadyImported).toBe(2);
});
it("unchanged retries after explicit restoration cannot resurrect old blocks", async () => {
    await pg.exec(
        "INSERT INTO podcast_deny_list VALUES(1,1,'apple','123','https://feed.test/rss','Reason','admin','2026-01-01',NULL,NULL)",
    );
    const old = await plan("podcast_deny_list");
    await applyMigration(store, old, "operator");
    const id = await domainId("podcast", 1);
    await pg.exec(
        "UPDATE podcast_deny_list SET restored_at='2026-02-01',restored_by='restorer'",
    );
    await restoreImportedDecision(store, {
        id,
        expectedVersion: 1,
        actor: "operator",
        reason: "Legacy restoration verified",
    });
    await expect(applyMigration(store, old, "operator")).rejects.toThrow(
        "snapshot changed",
    );
    expect((await apply("podcast_deny_list")).held).toBe(0);
    expect((await migrationCompatibility(store, id)).current.disposition).toBe(
        "pending",
    );
    expect(await rows("curation_decisions")).toHaveLength(2);
});

it("preserves scoped observation and publication references", async () => {
    await pg.exec(
        `INSERT INTO comedy_event_candidates VALUES(1,7,'event-key'); INSERT INTO comedy_event_decisions VALUES(1,1,'{}'); INSERT INTO comedy_event_reviews VALUES(1,1,1,'reject','admin','Scoped','p','i',2,3,'2026-01-01'); INSERT INTO comedy_event_observations VALUES(1,3,1,'baseline'); INSERT INTO comedy_event_publications VALUES(1,1,123);`,
    );
    const p = await plan("comedy_event_reviews");
    expect(
        p.items[0].context.observations[0].baseline_identity_fingerprint,
    ).toBe("baseline");
    expect(p.items[0].context.publications[0].show_id).toBe(123);
    await applyMigration(store, p, "operator");
    expect(await rows("curation_decisions")).toHaveLength(0);
});
it("recognizes a current ownership-review hostship audit without inventing attribution", async () => {
    await pg.exec(`INSERT INTO comedian_podcasts VALUES(1,1,1,'admin','host','accepted','human','2026-01-01','{}');
 INSERT INTO admin_action_audits(id,entity_type,entity_id,actor_profile_id,action,before_json,after_json,reason,created_at)
 SELECT 1,'podcast','1','human','podcast_hostship_review.approve','{}',jsonb_build_object('hostships',jsonb_build_array(jsonb_build_object('id',id,'comedianId',comedian_id,'podcastId',podcast_id,'associationType',association_type,'source',source,'reviewStatus',review_status,'reviewedBy',reviewed_by,'reviewedAt',reviewed_at))),'Confirmed host','2026-01-01' FROM comedian_podcasts;`);
    expect((await apply("comedian_podcasts")).held).toBe(0);
    expect((await rows("curation_relationships"))[0].disposition).toBe(
        "confirmed",
    );
    expect((await rows("curation_decisions"))[0].actor).toBe("human");
});

it("reports empty legacy names instead of silently omitting them from pagination", async () => {
    await pg.exec(
        "INSERT INTO comedian_deny_list VALUES('','Invalid empty name','audit','2026-01-01'),('Valid name','Denied','audit','2026-01-01')",
    );
    const first = await plan("comedian_deny_list", { limit: 1 });
    expect(first.items[0].key).toBe("");
    expect(first.items[0].conflicts).toHaveLength(1);
    expect(first.nextCursor).toBe("");
    expect((await applyMigration(store, first, "operator")).held).toBe(1);
    const next = await plan("comedian_deny_list", {
        limit: 1,
        after: first.nextCursor,
    });
    expect(next.items[0].key).toBe("Valid name");
    expect((await applyMigration(store, next, "operator")).imported).toBe(1);
});
