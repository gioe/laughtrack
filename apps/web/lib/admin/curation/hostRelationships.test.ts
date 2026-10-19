import { PGlite } from "@electric-sql/pglite";
import { Prisma } from "@prisma/client";
import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { beforeAll, beforeEach, afterAll, it, expect } from "vitest";
import { createHostRelationshipService } from "./hostRelationships";
import { createParentRelationshipService } from "./parentRelationships";
import type { Store } from "./decisions";
let pg: PGlite;
const raw =
    (conn: Pick<PGlite, "query">) =>
    async <T>(q: Prisma.Sql) =>
        (await conn.query(q.text, q.values)).rows as T;
const store: Store = {
    $queryRaw: (q) => raw(pg)(q),
    $transaction: (fn) => pg.transaction((tx) => fn({ $queryRaw: raw(tx) })),
};
const service = createHostRelationshipService(store, async () => {});
const parents = createParentRelationshipService(store, async () => {});
beforeAll(
    async () => {
        pg = new PGlite();
        await pg.exec(`CREATE TABLE comedians(id serial PRIMARY KEY,uuid text UNIQUE,name text,visible boolean DEFAULT true,parent_comedian_id int,identity_validated_at timestamptz,identity_validated_by text,block_reason text,block_added_by text,block_added_at timestamptz,total_shows int DEFAULT 0,instagram_followers int,bandsintown_id text);
 CREATE TABLE clubs(id int PRIMARY KEY); CREATE TABLE shows(id int PRIMARY KEY,name text,date timestamptz);
 CREATE TABLE comedian_deny_list(name text PRIMARY KEY); CREATE TABLE lineup_items(show_id int,comedian_id text REFERENCES comedians(uuid),UNIQUE(show_id,comedian_id));
 CREATE TABLE podcasts(id serial PRIMARY KEY,source text,source_podcast_id text,title text,feed_url text,external_ids jsonb DEFAULT '{}',UNIQUE(source,source_podcast_id));
 CREATE TABLE podcast_episodes(id serial PRIMARY KEY,podcast_id int REFERENCES podcasts,title text);
 CREATE TABLE podcast_deny_list(id serial PRIMARY KEY,podcast_id int REFERENCES podcasts ON DELETE SET NULL,source text,source_podcast_id text,feed_url text,reason text,denied_by text,denied_at timestamptz DEFAULT now(),restored_at timestamptz,restored_by text);
 CREATE TABLE comedian_podcasts(id serial PRIMARY KEY,comedian_id int,podcast_id int,association_type text,source text,review_status text DEFAULT 'pending',confidence float DEFAULT 1,evidence jsonb DEFAULT '{}',reviewed_at timestamptz,reviewed_by text,created_at timestamptz DEFAULT now(),updated_at timestamptz DEFAULT now(),UNIQUE(comedian_id,podcast_id,association_type,source));
 CREATE TABLE podcast_candidate_reviews(id serial PRIMARY KEY,comedian_id int,podcast_id int,association_type text,source text,source_podcast_id text,candidate_status text DEFAULT 'pending',confidence float DEFAULT 1,evidence jsonb DEFAULT '{}',reviewed_at timestamptz,reviewed_by text,created_at timestamptz DEFAULT now(),updated_at timestamptz DEFAULT now());
 CREATE INDEX ON comedian_podcasts(podcast_id); CREATE INDEX ON podcast_candidate_reviews(podcast_id); CREATE INDEX ON comedians(parent_comedian_id);
 CREATE TABLE show_publication_revision(id int PRIMARY KEY,revision bigint DEFAULT 0); INSERT INTO show_publication_revision VALUES(1,0);`);
        for (const name of [
            "20261012210000_comedian_identity_review",
            "20261014010000_durable_curation_model",
            "20261014190000_comedian_curation_intake",
            "20261015210000_podcast_curation_intake",
            "20261016180000_parent_relationship_curation",
        ])
            await pg.exec(
                readFileSync(`prisma/migrations/${name}/migration.sql`, "utf8"),
            );
        if (process.env.CURATION_HOST_SNAPSHOT) {
            console.log("snapshot: base schema ready");
            const snapshot = JSON.parse(
                readFileSync(process.env.CURATION_HOST_SNAPSHOT, "utf8"),
            )[0].snapshot;
            await pg.exec(
                "ALTER TABLE comedians DISABLE TRIGGER USER; ALTER TABLE podcasts DISABLE TRIGGER USER;",
            );
            await pg.query(
                "INSERT INTO comedians(id,uuid,name,parent_comedian_id) SELECT id,uuid,name,parent_comedian_id FROM jsonb_to_recordset($1::jsonb) AS x(id int,uuid text,name text,parent_comedian_id int)",
                [JSON.stringify(snapshot.comedians)],
            );
            await pg.query(
                "INSERT INTO podcasts(id,source,source_podcast_id,title) SELECT id,source,source_podcast_id,title FROM jsonb_to_recordset($1::jsonb) AS x(id int,source text,source_podcast_id text,title text)",
                [JSON.stringify(snapshot.podcasts)],
            );
            await pg.exec(
                "ALTER TABLE comedians ENABLE TRIGGER USER; ALTER TABLE podcasts ENABLE TRIGGER USER; INSERT INTO curation_entities(id,kind,label,podcast_id) SELECT 'snapshot-podcast:'||id,'podcast',title,id FROM podcasts;",
            );
            await pg.query(
                "INSERT INTO comedian_podcasts(id,comedian_id,podcast_id,association_type,source,review_status,evidence) SELECT id,comedian_id,podcast_id,association_type,source,review_status,evidence FROM jsonb_to_recordset($1::jsonb) AS x(id int,comedian_id int,podcast_id int,association_type text,source text,review_status text,evidence jsonb)",
                [JSON.stringify(snapshot.associations)],
            );
            await pg.query(
                "INSERT INTO podcast_candidate_reviews(id,comedian_id,podcast_id,association_type,source,candidate_status,evidence) SELECT id,comedian_id,podcast_id,association_type,source,candidate_status,evidence FROM jsonb_to_recordset($1::jsonb) AS x(id int,comedian_id int,podcast_id int,association_type text,source text,candidate_status text,evidence jsonb)",
                [JSON.stringify(snapshot.candidates)],
            );
            console.log("snapshot: rows loaded");
            const migration = readFileSync(
                "prisma/migrations/20261017150000_host_relationship_curation/migration.sql",
                "utf8",
            );
            await expect(pg.exec(migration)).rejects.toThrow(
                /Reconcile legacy host decisions/,
            );
            console.log("snapshot: preflight refused unreconciled decisions");
            // Disposable-clone scenario only: retain legacy state as evidence and simulate
            // explicit reopening for review. The production migration never does this.
            await pg.exec(
                "UPDATE comedian_podcasts SET evidence=evidence||jsonb_build_object('snapshotState',review_status),review_status='pending'; UPDATE podcast_candidate_reviews SET evidence=evidence||jsonb_build_object('snapshotState',candidate_status),candidate_status='pending';",
            );
            console.log("snapshot: applying reconciled staging scenario");
            await pg.exec(migration);
            console.log("snapshot: migration applied");
            expect(
                (
                    await pg.query<{ n: number }>(
                        "SELECT count(*)::int n FROM comedian_podcasts",
                    )
                ).rows[0].n,
            ).toBe(snapshot.associations.length);
            expect(
                (
                    await pg.query<{ n: number }>(
                        "SELECT count(*)::int n FROM podcast_candidate_reviews",
                    )
                ).rows[0].n,
            ).toBe(snapshot.candidates.length);
            expect(
                (
                    await pg.query(
                        "SELECT id FROM curation_relationships WHERE disposition='confirmed'",
                    )
                ).rows,
            ).toHaveLength(0);
            console.log(
                `Production-shaped migration: ${snapshot.associations.length} associations, ${snapshot.candidates.length} candidates; unreconciled decisions refused, source rows retained without approval.`,
            );
        } else
            await pg.exec(
                readFileSync(
                    "prisma/migrations/20261017150000_host_relationship_curation/migration.sql",
                    "utf8",
                ),
            );
    },
    process.env.CURATION_HOST_SNAPSHOT ? 300000 : 30000,
);
afterAll(async () => pg.close());
beforeEach(async () => {
    await pg.exec(
        "TRUNCATE curation_entities,comedians,clubs,shows,podcasts,comedian_deny_list,comedian_identity_candidates,comedian_podcasts,podcast_candidate_reviews CASCADE",
    );
});
async function person(name: string) {
    const uuid = randomUUID();
    await pg.query(
        "SELECT curation_approve_comedian($1,$2,'admin','Verified identity')",
        [uuid, name],
    );
    return (
        await pg.query<{ id: number }>(
            "INSERT INTO comedians(uuid,name,identity_validated_at,identity_validated_by) VALUES($1,$2,now(),'admin') RETURNING id",
            [uuid, name],
        )
    ).rows[0].id;
}
async function podcast() {
    const p = (
        await pg.query<{ id: number }>(
            "INSERT INTO podcasts(source,source_podcast_id,title) VALUES('test',$1,'A podcast') RETURNING id",
            [randomUUID()],
        )
    ).rows[0].id;
    await entity(p, "approve");
    return p;
}
async function entity(p: number, action: string) {
    await pg.query(
        "INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason) SELECT gen_random_uuid()::text,id,version+1,$2,disposition,CASE $2 WHEN 'approve' THEN 'approved' WHEN 'block' THEN 'blocked' ELSE 'pending' END,'admin','Reviewed podcast' FROM curation_entities WHERE podcast_id=$1",
        [p, action],
    );
}
async function observe(c: number, p: number, source = "itunes", role = "host") {
    return service.propose(
        {
            comedianId: c,
            podcastId: p,
            role,
            source,
            sourceKey: source + "-42",
            evidence: { url: "https://example.org/credits" },
            reason: "Observed credits",
        },
        "admin",
    );
}
async function decide(id: string, action: string, version?: number) {
    const [row] = (
        await pg.query<{ kind: string; version: number }>(
            "SELECT kind,version FROM curation_relationships WHERE id=$1",
            [id],
        )
    ).rows;
    return service.submit(
        {
            requestId: randomUUID(),
            target: { type: "relationship", id, kind: row.kind },
            expectedVersion: version ?? row.version,
            action,
            reason: "Reviewed host credits",
        },
        "admin",
    );
}
async function accepted(p: number) {
    return (
        await pg.query<{ comedian_id: number; association_type: string }>(
            "SELECT comedian_id,association_type FROM comedian_podcasts WHERE podcast_id=$1 AND review_status='accepted' ORDER BY comedian_id",
            [p],
        )
    ).rows;
}
async function parent(c: number, p: number | null) {
    if (p)
        await parents.propose(
            {
                childId: c,
                parentId: p,
                reason: "Verified alias",
                evidence: {
                    samePerformer: true,
                    sourceUrl: "https://example.org/bio",
                    explanation:
                        "Biography explicitly confirms both performer names.",
                },
            },
            "admin",
        );
    const x = {
        childId: c,
        parentId: p,
        reason: "Verified alias",
        requestId: randomUUID(),
    };
    const plan = await parents.preview(x);
    return parents.submit({ ...x, previewToken: plan.previewToken }, "admin");
}
it("retains multiple hosts and cohosts, projecting one accepted pair across all sources", async () => {
    const a = await person("Person A"),
        b = await person("Person B"),
        p = await podcast();
    const first = await observe(a, p);
    expect((await observe(a, p, "index")).relationshipId).toBe(
        first.relationshipId,
    );
    await pg.query(
        "INSERT INTO podcast_candidate_reviews(comedian_id,podcast_id,association_type,source,candidate_status) VALUES($1,$2,'host','itunes','accepted'),($1,$2,'host','index','pending')",
        [a, p],
    );
    expect(await accepted(p)).toHaveLength(0);
    expect((await decide(first.relationshipId, "confirm")).status).toBe(
        "applied",
    );
    const second = await observe(b, p, "manual", "cohost");
    await decide(second.relationshipId, "confirm");
    expect(await accepted(p)).toEqual([
        { comedian_id: a, association_type: "host" },
        { comedian_id: b, association_type: "cohost" },
    ]);
    expect(
        (
            await pg.query(
                "SELECT candidate_status,reviewed_by FROM podcast_candidate_reviews",
            )
        ).rows,
    ).toEqual([
        { candidate_status: "accepted", reviewed_by: "admin" },
        { candidate_status: "accepted", reviewed_by: "admin" },
    ]);
    const history = await service.history(p);
    expect(
        history.find((x) => x.id === first.relationshipId)?.observations.length,
    ).toBeGreaterThanOrEqual(4);
});
it("retains rejection across source and alias retries and requires restore then confirm", async () => {
    const a = await person("Person A"),
        alias = await person("Stage A"),
        p = await podcast();
    await parent(alias, a);
    const edge = await observe(a, p);
    await decide(edge.relationshipId, "reject");
    expect((await observe(alias, p, "other")).relationshipId).toBe(
        edge.relationshipId,
    );
    await pg.query(
        "INSERT INTO comedian_podcasts(comedian_id,podcast_id,association_type,source,review_status) VALUES($1,$2,'host','other','accepted')",
        [alias, p],
    );
    expect(await accepted(p)).toHaveLength(0);
    await expect(decide(edge.relationshipId, "confirm")).rejects.toThrow(
        /explicitly restored/,
    );
    await decide(edge.relationshipId, "restore");
    expect(await accepted(p)).toHaveLength(0);
    await decide(edge.relationshipId, "confirm");
    expect(await accepted(p)).toEqual([
        { comedian_id: a, association_type: "host" },
    ]);
});
it("severs only the chosen pair, retains evidence and is not restored by entity restoration", async () => {
    const a = await person("A"),
        b = await person("B"),
        p = await podcast();
    const first = await observe(a, p),
        second = await observe(b, p);
    await decide(first.relationshipId, "confirm");
    await decide(second.relationshipId, "confirm");
    await decide(first.relationshipId, "sever");
    expect(await accepted(p)).toEqual([
        { comedian_id: b, association_type: "host" },
    ]);
    await entity(p, "block");
    await entity(p, "restore");
    await entity(p, "approve");
    expect(await accepted(p)).toEqual([
        { comedian_id: b, association_type: "host" },
    ]);
    await observe(a, p, "retry");
    expect(
        (await service.history(p)).find((x) => x.id === first.relationshipId)
            ?.disposition,
    ).toBe("severed");
});
it("holds conflicting canonical changes for explicit review without merging decisions", async () => {
    const a = await person("A"),
        b = await person("B"),
        p = await podcast();
    const first = await observe(a, p),
        second = await observe(b, p);
    await decide(first.relationshipId, "confirm");
    await decide(second.relationshipId, "reject");
    await parent(a, b);
    expect(await accepted(p)).toHaveLength(0);
    expect((await observe(a, p, "new-source")).relationshipId).toBe(
        second.relationshipId,
    );
    const holds = (
        await pg.query<{ id: string }>(
            "SELECT id FROM curation_host_reconciliations WHERE resolved_at IS NULL",
        )
    ).rows;
    expect(holds.length).toBeGreaterThan(0);
    for (const h of holds) {
        const plan = await service.previewReconciliation(h.id);
        expect(plan.effects.join(" ")).toContain(
            "Retain old decision: confirmed; retain new decision: rejected",
        );
        await service.reconcile(
            {
                id: h.id,
                requestId: randomUUID(),
                token: plan.token,
                reason: "Explicitly retain both decisions after identity review",
            },
            "admin",
        );
    }
    expect(await accepted(p)).toHaveLength(0);
    await decide(second.relationshipId, "restore");
    await decide(second.relationshipId, "confirm");
    expect(await accepted(p)).toEqual([
        { comedian_id: b, association_type: "host" },
    ]);
});
it("protects stale versions and ineligible endpoints", async () => {
    const a = await person("A"),
        p = await podcast(),
        edge = await observe(a, p);
    await decide(edge.relationshipId, "reject");
    await expect(decide(edge.relationshipId, "restore", 0)).rejects.toThrow(
        /changed/,
    );
    await decide(edge.relationshipId, "restore");
    await entity(p, "block");
    await expect(decide(edge.relationshipId, "confirm")).rejects.toThrow(
        /conflicts with current/,
    );
    expect(await accepted(p)).toHaveLength(0);
});

it("rejects raw projection deletion/rekey and retains unbound source evidence", async () => {
    const a = await person("A"),
        b = await person("B"),
        p = await podcast(),
        edge = await observe(a, p);
    await decide(edge.relationshipId, "confirm");
    await expect(
        pg.query("DELETE FROM comedian_podcasts WHERE source='curation'"),
    ).rejects.toThrow(/Sever/);
    await expect(
        pg.query(
            "UPDATE comedian_podcasts SET association_type='guest' WHERE source='curation'",
        ),
    ).rejects.toThrow(/immutable/);
    await expect(
        pg.query(
            "UPDATE comedian_podcasts SET comedian_id=$1 WHERE source='curation'",
            [b],
        ),
    ).rejects.toThrow(/immutable/);
    await pg.query(
        "INSERT INTO podcast_candidate_reviews(comedian_id,association_type,source,candidate_status,evidence) VALUES($1,'host','unbound','accepted','{\"note\":\"unbound source\"}')",
        [a],
    );
    expect(
        (
            await pg.query(
                "SELECT candidate_status FROM podcast_candidate_reviews WHERE source='unbound'",
            )
        ).rows,
    ).toEqual([{ candidate_status: "pending" }]);
    expect(
        (
            await pg.query(
                "SELECT id FROM curation_observations WHERE source='unbound'",
            )
        ).rows,
    ).toHaveLength(1);
});
it("invalidates public host projection when a confirmed alias becomes hidden", async () => {
    const a = await person("A"),
        alias = await person("Alias A"),
        p = await podcast();
    await parent(alias, a);
    const edge = await observe(a, p);
    await decide(edge.relationshipId, "confirm");
    expect(await accepted(p)).toHaveLength(1);
    await pg.query("UPDATE comedians SET visible=false WHERE id=$1", [alias]);
    expect(await accepted(p)).toHaveLength(0);
});
it("replays immutable requests without duplicating decisions and rejects conflicting reuse", async () => {
    const a = await person("A"),
        p = await podcast(),
        edge = await observe(a, p);
    const command = {
        requestId: randomUUID(),
        target: {
            type: "relationship",
            id: edge.relationshipId,
            kind: "host_of",
        },
        expectedVersion: 0,
        action: "confirm",
        reason: "Reviewed credits",
    };
    const preview = await service.preview(command);
    expect(preview.effects.join(" ")).toContain("Other hosts");
    expect((await service.submit(command, "admin")).status).toBe("applied");
    expect((await service.submit(command, "admin")).status).toBe("applied");
    expect(
        (
            await pg.query(
                "SELECT id FROM curation_decisions WHERE relationship_id=$1",
                [edge.relationshipId],
            )
        ).rows,
    ).toHaveLength(1);
    await expect(
        service.submit({ ...command, reason: "Changed" }, "admin"),
    ).rejects.toThrow(/request ID/i);
});
it("requires a fresh reconciliation preview after either decision changes", async () => {
    const a = await person("A"),
        b = await person("B"),
        p = await podcast(),
        edge = await observe(a, p);
    await decide(edge.relationshipId, "confirm");
    await parent(a, b);
    const [hold] = (
        await pg.query<{ id: string }>(
            "SELECT id FROM curation_host_reconciliations WHERE resolved_at IS NULL",
        )
    ).rows;
    const preview = await service.previewReconciliation(hold.id);
    await decide(edge.relationshipId, "sever");
    await expect(
        service.reconcile(
            {
                id: hold.id,
                requestId: randomUUID(),
                token: preview.token,
                reason: "Reviewed",
            },
            "admin",
        ),
    ).rejects.toThrow(/Preview.*again/);
    expect(
        (
            await pg.query(
                "SELECT id FROM curation_host_reconciliations WHERE resolved_at IS NULL",
            )
        ).rows,
    ).toHaveLength(1);
});

it("previews host attribution holds before an alias change", async () => {
    const a = await person("A"),
        b = await person("B"),
        p = await podcast(),
        edge = await observe(a, p);
    await decide(edge.relationshipId, "confirm");
    await parents.propose(
        {
            childId: a,
            parentId: b,
            reason: "Verified alias",
            evidence: {
                samePerformer: true,
                sourceUrl: "https://example.org/bio",
                explanation: "Official biography explicitly lists both names.",
            },
        },
        "admin",
    );
    const preview = await parents.preview({
        childId: a,
        parentId: b,
        reason: "Review identity effects",
        requestId: randomUUID(),
    });
    expect(preview.effects.join(" ")).toContain(
        "host source identities on hold",
    );
    expect(await accepted(p)).toHaveLength(1);
});

it("lists shared Inbox identities and relationships with evidence, durable blocked history and endpoint filters", async () => {
    const { createInbox } = await import("./inbox");
    const inbox = createInbox(store);
    const comic = await person("Inbox Comic"),
        pod = await podcast();
    const edge = await observe(comic, pod);
    await decide(edge.relationshipId, "confirm");
    const queue = (await inbox.get({
        view: "relationships",
        recordId: pod,
        endpointKind: "podcast",
        state: "confirmed",
    })) as import("./inboxTypes").InboxPage;
    expect(queue.items).toHaveLength(1);
    expect(queue.items[0]).toMatchObject({
        sourceRecordId: comic,
        targetRecordId: pod,
        state: "confirmed",
    });
    const detail = (await inbox.get({
        view: "relationships",
        id: edge.relationshipId,
    })) as import("./inboxTypes").InboxDetail;
    expect(detail.observations).toHaveLength(1);
    expect(detail.decisions[0].actor).toBe("admin");
    await entity(pod, "block");
    const blocked = (await inbox.get({
        view: "intake",
        kind: "podcast",
        state: "blocked",
        q: "podcast",
    })) as import("./inboxTypes").InboxPage;
    expect(blocked.items).toHaveLength(1);
    const podcastDetail = (await inbox.get({
        view: "intake",
        id: blocked.items[0].target.id,
    })) as import("./inboxTypes").InboxDetail;
    expect(podcastDetail.keys.length).toBeGreaterThan(0);
    expect(podcastDetail.decisions[0].action).toBe("block");
    const matches = (await inbox.get({
        lookup: "comedian",
        q: "Inbox Comic",
    })) as import("./inboxTypes").InboxPage;
    expect(matches.items[0].recordId).toBe(comic);
    expect(
        (
            (await inbox.get({
                q: "' OR 1=1 --",
            })) as import("./inboxTypes").InboxPage
        ).items,
    ).toHaveLength(0);
});
