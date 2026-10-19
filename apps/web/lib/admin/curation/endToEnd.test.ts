import { PGlite } from "@electric-sql/pglite";
import { Prisma } from "@prisma/client";
import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { beforeAll, afterAll, it, expect } from "vitest";
import { createCurationService, type Store, type Adapter } from "./decisions";
import { comedianAdapter } from "./comedianAdapter";
import { clubAdapter } from "./clubAdapter";
import { podcastAdapter } from "./podcastAdapter";
import { showAdapter } from "./showAdapter";
import { createParentRelationshipService } from "./parentRelationships";
import { createHostRelationshipService } from "./hostRelationships";
let pg: PGlite;
const raw =
    (c: Pick<PGlite, "query">) =>
    async <T>(q: Prisma.Sql) =>
        (await c.query(q.text, q.values)).rows as T;
const store: Store = {
    $queryRaw: (q) => raw(pg)(q),
    $transaction: (fn) => pg.transaction((tx) => fn({ $queryRaw: raw(tx) })),
};
const adapters: Record<string, Adapter> = {
    comedian: comedianAdapter,
    club: clubAdapter,
    show: showAdapter,
    podcast: podcastAdapter,
};
const service = () =>
    createCurationService({
        store,
        adapter: (t) => adapters[t.kind],
        invalidate: async () => {},
    });
const parents = createParentRelationshipService(store, async () => {});
const hosts = createHostRelationshipService(store, async () => {});
async function rows(sql: string, args: any[] = []) {
    return (await pg.query<any>(sql, args)).rows;
}
async function entity(id: string, action: string) {
    const [e] = await rows("SELECT * FROM curation_entities WHERE id=$1", [id]);
    const command = {
        requestId: randomUUID(),
        target: { type: "entity", id, kind: e.kind, scope: e.identity_scope },
        expectedVersion: e.version,
        action,
        reason: "Reviewed fixture evidence",
    };
    const result = await service().submit(command, "admin");
    if (result.status === "pending")
        return service().process(command.requestId);
    return result;
}
async function person(name: string) {
    const uuid = randomUUID();
    await rows(
        "SELECT curation_approve_comedian($1,$2,'admin','Verified fixture performer')",
        [uuid, name],
    );
    return (
        await rows(
            "INSERT INTO comedians(uuid,name,identity_validated_at,identity_validated_by) VALUES($1,$2,now(),'admin') RETURNING *",
            [uuid, name],
        )
    )[0];
}
async function parent(childId: number, parentId: number | null) {
    if (parentId)
        await parents.propose(
            {
                childId,
                parentId,
                reason: "Verified alias",
                evidence: {
                    samePerformer: true,
                    sourceUrl: "https://example.org/bio",
                    explanation:
                        "Biography explicitly identifies both names as the same performer.",
                },
            },
            "admin",
        );
    const c = {
        childId,
        parentId,
        reason: "Reviewed relationship",
        requestId: randomUUID(),
    };
    const p = await parents.preview(c);
    return parents.submit({ ...c, previewToken: p.previewToken }, "admin");
}
async function host(c: number, p: number, source: string) {
    return hosts.propose(
        {
            comedianId: c,
            podcastId: p,
            role: "host",
            source,
            sourceKey: source + "-1",
            evidence: { url: "https://example.org/credits" },
            reason: "Verified credits",
        },
        "admin",
    );
}
async function edge(id: string, action: string) {
    const [r] = await rows("SELECT * FROM curation_relationships WHERE id=$1", [
        id,
    ]);
    return hosts.submit(
        {
            requestId: randomUUID(),
            target: { type: "relationship", id, kind: r.kind },
            expectedVersion: r.version,
            action,
            reason: "Reviewed credits",
        },
        "admin",
    );
}
beforeAll(async () => {
    pg = new PGlite();
    await pg.exec(
        readFileSync("lib/admin/curation/fixtures/endToEnd.sql", "utf8"),
    );
    for (const m of JSON.parse(
        readFileSync("lib/admin/curation/fixtures/migrations.json", "utf8"),
    ))
        await pg.exec(
            readFileSync(`prisma/migrations/${m}/migration.sql`, "utf8"),
        );
    await pg.exec(readFileSync("prisma/curation-health.sql", "utf8"));
}, 30000);
afterAll(async () => pg.close());
it("enforces the complete publication graph under all migrations, legacy writers and rediscovery", async () => {
    const a = await person("Fixture Alice"),
        alias = await person("Fixture Alice Alias"),
        b = await person("Fixture Bob");
    await parent(alias.id, a.id);
    const venue = {
        name: "Fixture Room",
        address: "1 Main St, Boston, MA",
        city: "Boston",
        state: "MA",
        website: "https://example.org",
    };
    const [observed] = await rows(
        "SELECT curation_observe_club($1::jsonb) id",
        [JSON.stringify(venue)],
    );
    expect((await entity(observed.id, "approve")).status).toBe("applied");
    const [club] = await rows("SELECT * FROM clubs WHERE name=$1", [
        venue.name,
    ]);
    const [source] = await rows(
        "INSERT INTO scraping_sources(club_id,platform) VALUES($1,'test') RETURNING id",
        [club.id],
    );
    const show = {
        club_id: club.id,
        source_id: source.id,
        name: "Fixture Night",
        date: "2028-01-01T20:00:00Z",
        source_performance_id: "native-1",
        url: "https://example.org/events/1",
    };
    const [occurrence] = await rows(
        "SELECT curation_observe_show($1::jsonb) id",
        [JSON.stringify(show)],
    );
    expect((await entity(occurrence.id, "approve")).status).toBe("applied");
    const [published] = await rows(
        "INSERT INTO shows(name,club_id,date,source_performance_id,show_page_url) VALUES($1,$2,$3,$4,$5) RETURNING id",
        [show.name, club.id, show.date, show.source_performance_id, show.url],
    );
    await rows("INSERT INTO lineup_items(show_id,comedian_id) VALUES($1,$2)", [
        published.id,
        alias.uuid,
    ]);
    const [pod] = await rows(
        "INSERT INTO podcasts(source,source_podcast_id,title,feed_url) VALUES('itunes','fixture-1','Fixture Podcast','https://example.org/feed') RETURNING id",
    );
    const [pe] = await rows(
        "SELECT id FROM curation_entities WHERE podcast_id=$1",
        [pod.id],
    );
    await entity(pe.id, "approve");
    const first = await host(a.id, pod.id, "itunes");
    await edge(first.relationshipId, "confirm");
    const other = await host(b.id, pod.id, "index");
    await edge(other.relationshipId, "confirm");
    await edge(first.relationshipId, "sever");
    expect(
        (await host(alias.id, pod.id, "other-provider")).relationshipId,
    ).toBe(first.relationshipId);
    await rows(
        "INSERT INTO comedian_podcasts(comedian_id,podcast_id,association_type,source,review_status) VALUES($1,$2,'host','legacy-import','accepted')",
        [alias.id, pod.id],
    );
    expect(
        await rows(
            "SELECT comedian_id FROM comedian_podcasts WHERE podcast_id=$1 AND review_status='accepted'",
            [pod.id],
        ),
    ).toEqual([{ comedian_id: b.id }]);
    await parent(alias.id, null);
    await expect(
        rows("UPDATE comedians SET parent_comedian_id=$1 WHERE id=$2", [
            a.id,
            alias.id,
        ]),
    ).rejects.toThrow();
    expect(
        (
            await rows("SELECT parent_comedian_id FROM comedians WHERE id=$1", [
                alias.id,
            ])
        )[0].parent_comedian_id,
    ).toBeNull();
    // A denied occurrence remains denied after its title, date and URL change.
    await entity(occurrence.id, "block");
    expect(
        (
            await rows("SELECT * FROM curation_show_policy($1::jsonb)", [
                JSON.stringify({
                    ...show,
                    name: "Changed title",
                    date: "2029-01-01",
                    url: "https://other.org",
                }),
            ])
        )[0].allowed,
    ).toBe(false);
    await rows("UPDATE shows SET visible=true WHERE id=$1", [published.id]);
    expect(
        (await rows("SELECT visible FROM shows WHERE id=$1", [published.id]))[0]
            .visible,
    ).toBe(false);
    await entity(occurrence.id, "restore");
    expect(
        (await rows("SELECT visible FROM shows WHERE id=$1", [published.id]))[0]
            .visible,
    ).toBe(false);
    // Blocking the club also closes source admission; restoration never enables it.
    await entity(observed.id, "block");
    await rows("UPDATE scraping_sources SET enabled=false WHERE id=$1", [
        source.id,
    ]);
    await rows("UPDATE scraping_sources SET enabled=true WHERE id=$1", [
        source.id,
    ]);
    expect(
        (
            await rows("SELECT enabled FROM scraping_sources WHERE id=$1", [
                source.id,
            ])
        )[0].enabled,
    ).toBe(false);
    await entity(observed.id, "restore");
    expect(
        (await rows("SELECT visible FROM clubs WHERE id=$1", [club.id]))[0]
            .visible,
    ).toBe(false);
    await entity(pe.id, "block");
    await expect(
        rows(
            "INSERT INTO podcasts(source,source_podcast_id,title,feed_url) VALUES('index','changed-known-id','New title','https://example.org/feed')",
        ),
    ).rejects.toThrow(/blocked/);
    expect(
        (await rows("SELECT curation_podcast_allowed($1) allowed", [pod.id]))[0]
            .allowed,
    ).toBe(false);
    await entity(pe.id, "restore");
    expect(
        (await rows("SELECT curation_podcast_allowed($1) allowed", [pod.id]))[0]
            .allowed,
    ).toBe(false);
    expect(
        (
            await rows(
                "SELECT disposition FROM curation_relationships WHERE id=$1",
                [first.relationshipId],
            )
        )[0].disposition,
    ).toBe("severed");
    const [ae] = await rows(
        "SELECT id FROM curation_entities WHERE comedian_id=$1",
        [a.id],
    );
    await entity(ae.id, "block");
    expect(
        await rows(
            "INSERT INTO comedians(uuid,name) VALUES($1,'Fixture Alice') RETURNING id",
            [randomUUID()],
        ),
    ).toHaveLength(0);
    await rows("UPDATE comedians SET visible=true WHERE id=$1", [a.id]);
    expect(
        (
            await rows(
                "SELECT disposition FROM curation_comedian_policy($1,$2,$3)",
                [a.uuid, a.name, a.id],
            )
        )[0].disposition,
    ).toBe("blocked");
    await entity(ae.id, "restore");
    expect(
        (await rows("SELECT visible FROM comedians WHERE id=$1", [b.id]))[0]
            .visible,
    ).toBe(true);
    expect(
        (
            await rows(
                "SELECT disposition FROM curation_relationships WHERE id=$1",
                [other.relationshipId],
            )
        )[0].disposition,
    ).toBe("confirmed");
});
it("rolls back partial application, resumes reserved work, and rejects stale approval after a block", async () => {
    const [p] = await rows(
        "INSERT INTO podcasts(source,source_podcast_id,title) VALUES('test','worker-fixture','Worker fixture') RETURNING id",
    );
    const [e] = await rows(
        "SELECT * FROM curation_entities WHERE podcast_id=$1",
        [p.id],
    );
    const command = {
        requestId: randomUUID(),
        target: { type: "entity", id: e.id, kind: "podcast", scope: "entity" },
        expectedVersion: e.version,
        action: "approve",
        reason: "Reviewed podcast evidence",
    };
    const worker = () =>
        createCurationService({
            store,
            adapter: () => ({ ...podcastAdapter, mode: "worker" }),
            invalidate: async () => {},
        });
    expect((await worker().submit(command, "admin")).status).toBe("pending");
    // A new service instance represents a restarted process with a durable request.
    expect((await worker().process(command.requestId)).status).toBe("applied");
    expect((await worker().process(command.requestId)).status).toBe("applied");
    await entity(e.id, "block");
    await entity(e.id, "restore");
    const [current] = await rows(
        "SELECT version FROM curation_entities WHERE id=$1",
        [e.id],
    );
    const retry = {
        ...command,
        requestId: randomUUID(),
        expectedVersion: current.version,
    };
    const broken = createCurationService({
        store,
        adapter: () => ({
            ...podcastAdapter,
            mode: "worker",
            apply: async (tx) => {
                await tx.$queryRaw(
                    Prisma.sql`UPDATE podcasts SET title='Partial effect' WHERE id=${p.id} RETURNING id`,
                );
                throw new Error("worker interrupted");
            },
        }),
        invalidate: async () => {},
    });
    await broken.submit(retry, "admin");
    expect((await broken.process(retry.requestId)).status).toBe("failed");
    expect(
        (await rows("SELECT title FROM podcasts WHERE id=$1", [p.id]))[0].title,
    ).toBe("Worker fixture");
    expect(
        (
            await rows(
                "SELECT disposition FROM curation_entities WHERE id=$1",
                [e.id],
            )
        )[0].disposition,
    ).toBe("pending");
    const stale = { ...retry, requestId: randomUUID() };
    await worker().submit(stale, "admin");
    await entity(e.id, "block");
    expect((await worker().process(stale.requestId)).status).toBe("conflict");
    expect(
        (await rows("SELECT curation_podcast_allowed($1) allowed", [p.id]))[0]
            .allowed,
    ).toBe(false);
    const unavailable = createCurationService({
        store: {
            $queryRaw: async () => {
                throw new Error("policy unavailable");
            },
            $transaction: async () => {
                throw new Error("policy unavailable");
            },
        },
        adapter: () => podcastAdapter,
        invalidate: async () => {},
    });
    await expect(
        unavailable.submit({ ...command, requestId: randomUUID() }, "admin"),
    ).rejects.toThrow(/policy unavailable/);
    expect(
        (
            await rows(
                "SELECT disposition FROM curation_entities WHERE id=$1",
                [e.id],
            )
        )[0].disposition,
    ).toBe("blocked");
});
