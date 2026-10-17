import { PGlite } from "@electric-sql/pglite";
import { readFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { Prisma } from "@prisma/client";
import { beforeAll, beforeEach, afterAll, it, expect, vi } from "vitest";
import { createParentRelationshipService } from "./parentRelationships";
import { createCurationService, type Store } from "./decisions";
import { parentAdapter } from "./parentAdapter";
const dbMock = vi.hoisted(() => ({ findUnique: vi.fn(), findMany: vi.fn() }));
vi.mock("@/lib/db", () => ({ db: { comedian: dbMock } }));
import { resolveCanonicalComedianIdentityById } from "@/lib/data/comedian/detail/resolveCanonicalComedianIdentity";
let pg: PGlite;
const invalidate = vi.fn(async () => {});
function raw(conn: Pick<PGlite, "query">) {
    return async <T>(q: Prisma.Sql) =>
        (await conn.query(q.text, q.values)).rows as T;
}
const store: Store = {
    $queryRaw: (q) => raw(pg)(q),
    $transaction: (fn) => pg.transaction((tx) => fn({ $queryRaw: raw(tx) })),
};
const service = createParentRelationshipService(store, invalidate);
const generic = createCurationService({
    store,
    adapter: () => parentAdapter,
    invalidate,
});
const migration = readFileSync(
    "prisma/migrations/20261016180000_parent_relationship_curation/migration.sql",
    "utf8",
);
beforeAll(async () => {
    pg = new PGlite();
    await pg.exec(`CREATE TABLE comedians(id serial PRIMARY KEY,uuid text UNIQUE,name text,visible boolean DEFAULT true,parent_comedian_id int,identity_validated_at timestamptz,identity_validated_by text,block_reason text,block_added_by text,block_added_at timestamptz,total_shows int DEFAULT 0,instagram_followers int,bandsintown_id text);
 CREATE TABLE clubs(id int PRIMARY KEY); CREATE TABLE podcasts(id int PRIMARY KEY); CREATE TABLE shows(id int PRIMARY KEY,name text,date timestamptz);
 CREATE TABLE comedian_deny_list(name text PRIMARY KEY); CREATE TABLE lineup_items(show_id int,comedian_id text REFERENCES comedians(uuid),UNIQUE(show_id,comedian_id));
 CREATE TABLE show_publication_revision(id int PRIMARY KEY,revision bigint DEFAULT 0); INSERT INTO show_publication_revision VALUES(1,0);`);
    for (const name of [
        "20261012210000_comedian_identity_review",
        "20261014010000_durable_curation_model",
        "20261014190000_comedian_curation_intake",
    ]) {
        await pg.exec(
            readFileSync(`prisma/migrations/${name}/migration.sql`, "utf8"),
        );
    }
    await pg.exec(migration);
}, 30000);
afterAll(async () => pg.close());
beforeEach(async () => {
    await pg.exec(
        "TRUNCATE curation_entities,comedians,clubs,podcasts,shows,comedian_deny_list,comedian_identity_candidates CASCADE",
    );
    invalidate.mockClear();
    dbMock.findUnique.mockImplementation(
        async ({ where }) =>
            (
                await pg.query(
                    'SELECT id,uuid,visible,parent_comedian_id AS "parentComedianId" FROM comedians WHERE id=$1',
                    [where.id],
                )
            ).rows[0],
    );
    dbMock.findMany.mockImplementation(
        async ({ where }) =>
            (
                await pg.query(
                    'SELECT id,uuid,visible,parent_comedian_id AS "parentComedianId" FROM comedians WHERE parent_comedian_id=ANY($1) ORDER BY id',
                    [where.parentComedianId.in],
                )
            ).rows,
    );
});
async function person(name: string) {
    const uuid = randomUUID();
    await pg.query(
        "SELECT curation_approve_comedian($1,$2,'admin','Verified identity')",
        [uuid, name],
    );
    const result = await pg.query<{ id: number }>(
        "INSERT INTO comedians(uuid,name,identity_validated_at,identity_validated_by) VALUES($1,$2,now(),'admin') RETURNING id",
        [uuid, name],
    );
    return result.rows[0].id;
}
const evidence = {
    samePerformer: true,
    sourceUrl: "https://example.org/performer",
    explanation:
        "The performer biography explicitly identifies both stage names.",
};
async function proposal(childId: number, parentId: number) {
    return service.propose(
        { childId, parentId, reason: "Verified stage name", evidence },
        "admin",
    );
}
async function change(childId: number, parentId: number | null) {
    const command = {
        childId,
        parentId,
        reason: "Reviewed performer relationship",
        requestId: randomUUID(),
    };
    return { ...command, ...(await service.preview(command)) };
}
async function apply(childId: number, parentId: number | null) {
    const x = await change(childId, parentId);
    return service.submit(
        {
            childId,
            parentId,
            reason: x.reason,
            requestId: x.requestId,
            previewToken: x.previewToken,
        },
        "admin",
    );
}
async function decision(id: string, action: string) {
    const [edge] = (
        await pg.query<{ version: number }>(
            "SELECT version FROM curation_relationships WHERE id=$1",
            [id],
        )
    ).rows;
    return generic.submit(
        {
            requestId: randomUUID(),
            target: { type: "relationship", kind: "alias_of", id },
            expectedVersion: edge.version,
            action,
            reason: "Explicitly reviewed relationship",
        },
        "admin",
    );
}
async function parent(childId: number) {
    return (
        await pg.query<{ parent_comedian_id: number | null }>(
            "SELECT parent_comedian_id FROM comedians WHERE id=$1",
            [childId],
        )
    ).rows[0].parent_comedian_id;
}
it("confirms only reviewed pairs, projects canonical grouping and preserves original appearances", async () => {
    const child = await person("Stage Name"),
        root = await person("Real Name");
    await pg.query(
        "INSERT INTO lineup_items SELECT 1,uuid FROM comedians WHERE id=$1",
        [child],
    );
    const original = (await pg.query("SELECT * FROM lineup_items")).rows;
    const { relationshipId } = await proposal(child, root);
    expect(await parent(child)).toBeNull();
    await expect(
        pg.query("UPDATE comedians SET parent_comedian_id=$1 WHERE id=$2", [
            root,
            child,
        ]),
    ).rejects.toThrow(/reviewed curation/);
    const preview = await change(child, root);
    expect(preview.effects.join(" ")).toMatch(/Preserve original lineup/);
    const command = {
        childId: child,
        parentId: root,
        reason: preview.reason,
        requestId: preview.requestId,
        previewToken: preview.previewToken,
    };
    expect((await service.submit(command, "admin")).status).toBe("applied");
    expect((await service.submit(command, "admin")).status).toBe("applied");
    expect(await parent(child)).toBe(root);
    expect((await resolveCanonicalComedianIdentityById(child))?.rootId).toBe(
        root,
    );
    expect(
        (
            await pg.query(
                "SELECT p.* FROM comedians c CROSS JOIN LATERAL curation_comedian_policy(c.uuid,c.name,c.id) p WHERE c.id=$1",
                [child],
            )
        ).rows[0],
    ).toMatchObject({ disposition: "approved", comedian_id: root });
    expect((await pg.query("SELECT * FROM lineup_items")).rows).toEqual(
        original,
    );
    expect((await service.history(child))[0].decisions).toEqual(
        expect.arrayContaining([
            expect.objectContaining({ action: "confirm", actor: "admin" }),
        ]),
    );
    expect(
        (
            await pg.query<{ revision: number }>(
                "SELECT revision FROM show_publication_revision",
            )
        ).rows[0].revision,
    ).not.toBe(0);
    expect((await decision(relationshipId, "sever")).status).toBe("applied");
    expect(await parent(child)).toBeNull();
    expect((await resolveCanonicalComedianIdentityById(child))?.rootId).toBe(
        child,
    );
    expect(
        (
            await pg.query(
                "SELECT p.* FROM comedians c CROSS JOIN LATERAL curation_comedian_policy(c.uuid,c.name,c.id) p WHERE c.id=$1",
                [child],
            )
        ).rows[0],
    ).toMatchObject({ disposition: "approved", comedian_id: child });
    expect(
        (
            await pg.query("SELECT disposition FROM curation_entities")
        ).rows.every((x: any) => x.disposition === "approved"),
    ).toBe(true);
});
it("retains rejected and severed pairs across sources until explicitly restored and confirmed", async () => {
    const child = await person("Alternate Name"),
        root = await person("Canonical Name");
    const { relationshipId } = await proposal(child, root);
    expect((await decision(relationshipId, "reject")).status).toBe("applied");
    await pg.query(
        "SELECT curation_propose_parent($1,$2,'{}','scraper','New source','other-source')",
        [child, root],
    );
    await expect(change(child, root)).rejects.toThrow(/Explicitly restore/);
    expect((await decision(relationshipId, "restore")).status).toBe("applied");
    expect(await parent(child)).toBeNull();
    expect((await apply(child, root)).status).toBe("applied");
    await apply(child, null);
    await proposal(child, root);
    await expect(change(child, root)).rejects.toThrow(/Explicitly restore/);
    expect(
        (await service.history(child))[0].decisions.map((d: any) => d.action),
    ).toEqual(["reject", "restore", "confirm", "sever"]);
});
it("requires independent evidence and prior identity approval, never a title substring", async () => {
    const child = await person("Real Name Comedy"),
        root = await person("Real Name");
    await pg.query(
        "SELECT curation_propose_parent($1,$2,$3::jsonb,'scraper','Name contained','automatic-alias-suggestion')",
        [child, root, JSON.stringify(evidence)],
    );
    await expect(change(child, root)).rejects.toThrow(
        /Independent same-performer/,
    );
    await proposal(child, root);
    await pg.query(
        "UPDATE comedians SET identity_validated_at=NULL,identity_validated_by=NULL WHERE id=$1",
        [child],
    );
    await expect(change(child, root)).rejects.toThrow(
        /independent identity approval/,
    );
    expect(await parent(child)).toBeNull();
});
it("replaces a parent atomically, retains negative history, and invalidates stale previews", async () => {
    const child = await person("Stage Name"),
        old = await person("Old Name"),
        next = await person("New Name");
    await proposal(child, old);
    await apply(child, old);
    await proposal(child, next);
    const x = await change(child, next);
    expect(x.effects[0]).toContain("Sever");
    await proposal(child, next); // duplicate evidence does not change the plan
    await apply(child, next);
    expect(await parent(child)).toBe(next);
    expect(
        (await service.history(child)).map((x) => x.disposition).sort(),
    ).toEqual(["confirmed", "severed"]);
    const newChild = await person("Third Name");
    await proposal(newChild, old);
    const stale = await change(newChild, old);
    await pg.query("UPDATE comedians SET visible=false WHERE id=$1", [old]);
    await expect(
        service.submit(
            {
                childId: newChild,
                parentId: old,
                reason: stale.reason,
                requestId: stale.requestId,
                previewToken: stale.previewToken,
            },
            "admin",
        ),
    ).rejects.toThrow();
    expect(await parent(newChild)).toBeNull();
});
it("rolls back an old-parent sever when replacement confirmation fails", async () => {
    const child = await person("Stage Name"),
        old = await person("Old Name"),
        next = await person("New Name");
    await proposal(child, old);
    await apply(child, old);
    await proposal(child, next);
    const x = await change(child, next);
    await pg.exec(
        `CREATE FUNCTION reject_test_confirm() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action='confirm' THEN RAISE EXCEPTION 'Injected confirmation failure'; END IF; RETURN NEW; END $$; CREATE TRIGGER zzz_test_failure AFTER INSERT ON curation_decisions FOR EACH ROW EXECUTE FUNCTION reject_test_confirm();`,
    );
    try {
        await expect(
            service.submit(
                {
                    childId: child,
                    parentId: next,
                    reason: x.reason,
                    requestId: x.requestId,
                    previewToken: x.previewToken,
                },
                "admin",
            ),
        ).rejects.toThrow();
    } finally {
        await pg.exec(
            "DROP TRIGGER zzz_test_failure ON curation_decisions; DROP FUNCTION reject_test_confirm()",
        );
    }
    expect(await parent(child)).toBe(old);
    expect(
        (await service.history(child)).map((x) => x.disposition).sort(),
    ).toEqual(["confirmed", "proposed"]);
});
it("rejects self, cyclic/noncanonical parent links and competing assignments", async () => {
    const a = await person("Person A"),
        b = await person("Person B"),
        c = await person("Person C");
    await expect(proposal(a, a)).rejects.toThrow(/own parent/);
    await proposal(a, b);
    await proposal(a, c);
    const x = await change(a, c);
    await apply(a, b);
    await expect(
        service.submit(
            {
                childId: a,
                parentId: c,
                reason: x.reason,
                requestId: x.requestId,
                previewToken: x.previewToken,
            },
            "admin",
        ),
    ).rejects.toThrow(/Preview again/);
    await proposal(b, a);
    await expect(change(b, a)).rejects.toThrow(/canonical parent/);
    const [{ id }] = (
        await pg.query<{ id: string }>(
            "SELECT r.id FROM curation_relationships r JOIN curation_entities e ON e.id=r.target_id WHERE e.comedian_id=$1",
            [c],
        )
    ).rows;
    expect((await decision(id, "confirm")).status).toBe("conflict");
    expect(await parent(a)).toBe(b);
});
it("can sever a relationship after an endpoint loses approval without restoring identity", async () => {
    const child = await person("Child"),
        root = await person("Parent");
    await proposal(child, root);
    await apply(child, root);
    await pg.query("UPDATE comedians SET visible=false WHERE id=$1", [root]);
    await apply(child, null);
    expect(await parent(child)).toBeNull();
    expect(
        (
            await pg.query<{ visible: boolean }>(
                "SELECT visible FROM comedians WHERE id=$1",
                [root],
            )
        ).rows[0].visible,
    ).toBe(false);
});

it("checks legacy projection drift before installing the new boundary", async () => {
    const clone = new PGlite();
    try {
        await clone.exec(
            `CREATE TABLE comedians(id int PRIMARY KEY,name text,uuid text,parent_comedian_id int); CREATE TABLE clubs(id int PRIMARY KEY); CREATE TABLE shows(id int PRIMARY KEY); CREATE TABLE podcasts(id int PRIMARY KEY);`,
        );
        await clone.exec(
            readFileSync(
                "prisma/migrations/20261014010000_durable_curation_model/migration.sql",
                "utf8",
            ),
        );
        const snapshotPath = process.env.CURATION_PARENT_SNAPSHOT;
        const pairs: {
            id: number;
            name: string;
            parent_comedian_id: number;
            parent_name: string;
        }[] = snapshotPath
            ? JSON.parse(readFileSync(snapshotPath, "utf8"))
            : [
                  {
                      id: 1,
                      name: "Stage Name",
                      parent_comedian_id: 2,
                      parent_name: "Canonical Name",
                  },
              ];
        const people = new Map<
            number,
            { name: string; parent: number | null }
        >();
        for (const p of pairs) {
            people.set(p.parent_comedian_id, {
                name: p.parent_name,
                parent: null,
            });
        }
        for (const p of pairs) {
            people.set(p.id, { name: p.name, parent: p.parent_comedian_id });
        }
        for (const [id, p] of people)
            await clone.query("INSERT INTO comedians VALUES($1,$2,$3,$4)", [
                id,
                p.name,
                String(id),
                p.parent,
            ]);
        await expect(clone.exec(migration)).rejects.toThrow(
            /Unreviewed legacy parent/,
        );
        // Simulate explicit reconciliation in the disposable clone only. This is not
        // an approval of the snapshot records and is never run against production.
        for (const [id, p] of people)
            await clone.query(
                "INSERT INTO curation_entities(id,kind,label,comedian_id) VALUES($1,'comedian',$2,$3)",
                [String(id), p.name, id],
            );
        for (const p of pairs) {
            const id = `pair-${p.id}`;
            await clone.query(
                "INSERT INTO curation_relationships(id,kind,source_id,target_id,target_kind) VALUES($1,'alias_of',$2,$3,'comedian')",
                [id, String(p.id), String(p.parent_comedian_id)],
            );
            await clone.query(
                "INSERT INTO curation_decisions(id,relationship_id,version,action,before_state,after_state,actor,reason) VALUES($1,$2,1,'confirm','proposed','confirmed','test-only','Simulated reconciliation in disposable clone')",
                [`${id}-confirm`, id],
            );
        }
        const first = pairs[0];
        await clone.query(
            "UPDATE comedians SET parent_comedian_id=NULL WHERE id=$1",
            [first.id],
        );
        await expect(clone.exec(migration)).rejects.toThrow(/ledger differs/);
        await clone.query(
            "UPDATE comedians SET parent_comedian_id=$1 WHERE id=$2",
            [first.parent_comedian_id, first.id],
        );
        await clone.exec(migration);
        expect(
            (
                await clone.query<{ n: number }>(
                    "SELECT count(*)::int n FROM comedians WHERE parent_comedian_id IS NOT NULL",
                )
            ).rows[0].n,
        ).toBe(pairs.length);
    } finally {
        await clone.close();
    }
}, 30000);

it("serializes competing submissions so only one previously previewed assignment commits", async () => {
    const child = await person("Concurrent Child"),
        a = await person("Parent A"),
        b = await person("Parent B");
    await proposal(child, a);
    await proposal(child, b);
    const commands = await Promise.all(
        [a, b].map(async (parentId) => {
            const x = await change(child, parentId);
            return {
                childId: child,
                parentId,
                reason: x.reason,
                requestId: x.requestId,
                previewToken: x.previewToken,
            };
        }),
    );
    const results = await Promise.allSettled(
        commands.map((x) => service.submit(x, "admin")),
    );
    expect(results.filter((x) => x.status === "fulfilled")).toHaveLength(1);
    expect(results.filter((x) => x.status === "rejected")).toHaveLength(1);
    expect(
        (await service.history(child)).filter(
            (x) => x.disposition === "confirmed",
        ),
    ).toHaveLength(1);
});
it("proposing a legacy unvalidated endpoint never approves it", async () => {
    const child = await person("Unvalidated Stage Name"),
        root = await person("Real Name");
    await pg.query(
        "INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason) SELECT 'block-child',id,version+1,'block',disposition,'blocked','admin','Identity needs review' FROM curation_entities WHERE comedian_id=$1",
        [child],
    );
    await pg.query(
        "INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason) SELECT 'restore-child',id,version+1,'restore',disposition,'pending','admin','Reopen identity review' FROM curation_entities WHERE comedian_id=$1",
        [child],
    );
    await proposal(child, root);
    await expect(change(child, root)).rejects.toThrow(/identity approval/);
    expect(
        (
            await pg.query<{ disposition: string }>(
                "SELECT disposition FROM curation_entities WHERE comedian_id=$1",
                [child],
            )
        ).rows[0].disposition,
    ).toBe("pending");
});
