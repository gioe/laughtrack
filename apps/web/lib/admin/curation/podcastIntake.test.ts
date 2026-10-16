import { Prisma } from "@prisma/client";
import { createCurationService, type SqlClient } from "./decisions";
import { podcastAdapter } from "./podcastAdapter";
import { PGlite } from "@electric-sql/pglite";
import { readFileSync } from "node:fs";
import { beforeAll, beforeEach, afterAll, it, expect } from "vitest";
let pg: PGlite;
beforeAll(
    async () => {
        pg = new PGlite();
        await pg.exec(`CREATE TABLE comedians(id serial PRIMARY KEY); CREATE TABLE clubs(id serial PRIMARY KEY); CREATE TABLE shows(id serial PRIMARY KEY);
 CREATE TABLE podcasts(id serial PRIMARY KEY,source text,source_podcast_id text,title text,feed_url text,external_ids jsonb DEFAULT '{}',UNIQUE(source,source_podcast_id));
 CREATE TABLE podcast_episodes(id serial PRIMARY KEY,podcast_id int REFERENCES podcasts,title text);
 CREATE TABLE podcast_deny_list(id serial PRIMARY KEY,podcast_id int REFERENCES podcasts ON DELETE SET NULL,source text,source_podcast_id text,feed_url text,reason text,denied_by text,denied_at timestamptz DEFAULT now(),restored_at timestamptz,restored_by text);
 CREATE TABLE show_publication_revision(id int PRIMARY KEY,revision bigint DEFAULT 0); INSERT INTO show_publication_revision(id) VALUES(1);`);
        await pg.exec(
            readFileSync(
                "prisma/migrations/20261014010000_durable_curation_model/migration.sql",
                "utf8",
            ),
        );
        await pg.exec(`CREATE TABLE curation_intake_lock(id int PRIMARY KEY,version bigint DEFAULT 0); INSERT INTO curation_intake_lock(id) VALUES(1);
 CREATE FUNCTION curation_lock_intake() RETURNS void LANGUAGE plpgsql AS $$ BEGIN UPDATE curation_intake_lock SET version=version+1 WHERE id=1; IF NOT FOUND THEN RAISE EXCEPTION 'Unavailable'; END IF; END $$;
 CREATE FUNCTION curation_serialize_intake() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN PERFORM curation_lock_intake(); RETURN NULL; END $$;`);
        if (process.env.CURATION_PODCAST_SNAPSHOT) {
            const { snapshot } = JSON.parse(
                readFileSync(process.env.CURATION_PODCAST_SNAPSHOT, "utf8"),
            )[0];
            for (const p of snapshot.podcasts ?? [])
                await pg.query(
                    "INSERT INTO podcasts(id,source,source_podcast_id,title,feed_url,external_ids) VALUES($1,$2,$3,$4,$5,$6::jsonb)",
                    [
                        p.id,
                        p.source,
                        p.source_podcast_id,
                        p.title,
                        p.feed_url,
                        JSON.stringify(p.external_ids),
                    ],
                );
            for (const d of snapshot.denials ?? [])
                await pg.query(
                    "INSERT INTO podcast_deny_list(id,podcast_id,source,source_podcast_id,feed_url,reason,denied_by,denied_at,restored_at,restored_by) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)",
                    [
                        d.id,
                        d.podcast_id,
                        d.source,
                        d.source_podcast_id,
                        d.feed_url,
                        d.reason,
                        d.denied_by,
                        d.denied_at,
                        d.restored_at,
                        d.restored_by,
                    ],
                );
            console.log(
                `Production-shaped migration: ${snapshot.podcasts.length} podcasts, ${snapshot.denials.length} historical denials`,
            );
        }
        await pg.exec(
            readFileSync(
                "prisma/migrations/20261015210000_podcast_curation_intake/migration.sql",
                "utf8",
            ),
        );
        expect(
            (
                await pg.query(
                    "SELECT * FROM curation_entities WHERE disposition='approved'",
                )
            ).rows,
        ).toHaveLength(0);
    },
    process.env.CURATION_PODCAST_SNAPSHOT ? 300000 : 30000,
);
afterAll(async () => pg.close());
beforeEach(async () => {
    await pg.exec(
        "TRUNCATE podcasts,curation_entities,podcast_deny_list CASCADE",
    );
});
async function insert(
    source = "itunes",
    id = "1",
    feed = "https://EXAMPLE.com:443/feed#fragment",
) {
    return (
        await pg.query<any>(
            "INSERT INTO podcasts(source,source_podcast_id,title,feed_url) VALUES($1,$2,$3,$4) RETURNING id",
            [source, id, "Same title", feed],
        )
    ).rows[0].id;
}
async function policy(payload: object) {
    return (
        await pg.query<any>(
            "SELECT * FROM curation_podcast_policy($1::jsonb)",
            [JSON.stringify(payload)],
        )
    ).rows[0];
}
async function decide(id: number, action: string) {
    await pg.query(
        `INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason) SELECT gen_random_uuid()::text,id,version+1,$2,disposition,CASE WHEN $2='approve' THEN 'approved' WHEN $2='block' THEN 'blocked' ELSE 'pending' END,'admin','Reviewed' FROM curation_entities WHERE podcast_id=$1`,
        [id, action],
    );
}
async function allowed(id: number) {
    return (
        await pg.query<any>("SELECT curation_podcast_allowed($1) allowed", [id])
    ).rows[0].allowed;
}
it("stages new podcasts and gates all episode writers until independent approval", async () => {
    const id = await insert();
    expect(await allowed(id)).toBe(false);
    await expect(
        pg.query(
            "INSERT INTO podcast_episodes(podcast_id,title) VALUES($1,'Episode')",
            [id],
        ),
    ).rejects.toThrow("held");
    await decide(id, "approve");
    expect(await allowed(id)).toBe(true);
    await pg.query(
        "INSERT INTO podcast_episodes(podcast_id,title) VALUES($1,'Episode')",
        [id],
    );
    await decide(id, "block");
    expect(await allowed(id)).toBe(false);
    await expect(
        pg.query(
            "UPDATE podcast_episodes SET title='Refreshed' WHERE podcast_id=$1",
            [id],
        ),
    ).rejects.toThrow("held");
    expect(
        (await pg.query("SELECT * FROM podcast_episodes")).rows,
    ).toHaveLength(1);
    await decide(id, "restore");
    expect(await allowed(id)).toBe(false);
    await decide(id, "approve");
    expect(await allowed(id)).toBe(true);
});
it("blocks cross-provider rediscovery, retains old feeds and never matches titles", async () => {
    const id = await insert();
    await decide(id, "approve");
    await pg.query("UPDATE podcasts SET feed_url=$1 WHERE id=$2", [
        "https://new.example/feed",
        id,
    ]);
    await decide(id, "block");
    expect(
        (
            await policy({
                source: "podcast_index",
                source_podcast_id: "77",
                feed_url: "https://example.com/feed",
            })
        ).disposition,
    ).toBe("blocked");
    await expect(
        insert("podcast_index", "77", "https://example.com/feed"),
    ).rejects.toThrow("blocked");
    const unrelated = await insert("itunes", "2", "https://other.example/feed");
    expect(await allowed(unrelated)).toBe(false);
    expect(
        (await policy({ feed_url: "https://example.com/Feed" })).disposition,
    ).toBe("pending");
    expect(
        (await policy({ feed_url: "http://example.com/feed" })).disposition,
    ).toBe("pending");
    expect(
        (await policy({ feed_url: "https://example.com/feed?x=1" }))
            .disposition,
    ).toBe("pending");
});
it("requires explicit feed alias evidence and refuses alias collisions", async () => {
    const id = await insert();
    const { entity_id } = await policy({ id });
    await pg.query("SELECT curation_verify_podcast_feed($1,$2,$3,$4)", [
        entity_id,
        "https://redirect.example/feed",
        "admin",
        "Verified feed ownership",
    ]);
    await decide(id, "block");
    expect(
        (await policy({ feed_url: "https://redirect.example/feed" }))
            .disposition,
    ).toBe("blocked");
    const other = await insert("itunes", "2", "https://other.example/feed");
    const entity = (await policy({ id: other })).entity_id;
    await expect(
        pg.query("SELECT curation_verify_podcast_feed($1,$2,$3,$4)", [
            entity,
            "https://redirect.example/feed",
            "admin",
            "Claim",
        ]),
    ).rejects.toThrow("another identity");
});
it("holds ambiguous provider/feed joins without poisoning either identity", async () => {
    const a = await insert();
    const b = await insert("itunes", "2", "https://other.example/feed");
    expect(
        (
            await policy({
                source: "itunes",
                source_podcast_id: "1",
                feed_url: "https://other.example/feed",
            })
        ).disposition,
    ).toBe("ambiguous");
    await expect(
        pg.query("UPDATE podcasts SET feed_url=$1 WHERE id=$2", [
            "https://other.example/feed",
            a,
        ]),
    ).rejects.toThrow("ambiguous");
    expect((await policy({ id: b })).disposition).toBe("pending");
});
it("retains legacy denial history and restores only to pending", async () => {
    const id = await insert();
    await decide(id, "approve");
    await pg.query(
        "INSERT INTO podcast_deny_list(podcast_id,feed_url,reason,denied_by) VALUES($1,$2,$3,$4)",
        [id, "https://example.com/feed", "No podcast", "admin"],
    );
    expect(await allowed(id)).toBe(false);
    await decide(id, "restore");
    expect(await allowed(id)).toBe(false);
    const d = (await pg.query<any>("SELECT * FROM podcast_deny_list")).rows[0];
    expect(d.restored_at).not.toBeNull();
    expect(d.reason).toBe("No podcast");
    await decide(id, "approve");
    expect(await allowed(id)).toBe(true);
});
it("preserves unbound legacy blocks even when compatibility rows are deleted", async () => {
    await pg.exec(
        "INSERT INTO podcast_deny_list(source,source_podcast_id,feed_url) VALUES('itunes','9','https://blocked.example/feed')",
    );
    await pg.exec("DELETE FROM podcast_deny_list");
    expect(
        (await policy({ source: "itunes", source_podcast_id: "9" }))
            .disposition,
    ).toBe("blocked");
    await expect(
        insert("podcast_index", "9", "https://blocked.example/feed"),
    ).rejects.toThrow("blocked");
});
it("retains identity after deletion and invalidates shared public caches", async () => {
    const id = await insert();
    await decide(id, "block");
    const before = (
        await pg.query<any>("SELECT revision FROM show_publication_revision")
    ).rows[0].revision;
    await decide(id, "restore");
    const after = (
        await pg.query<any>("SELECT revision FROM show_publication_revision")
    ).rows[0].revision;
    expect(Number(after)).toBeGreaterThan(Number(before));
    await decide(id, "block");
    await pg.query("DELETE FROM podcasts WHERE id=$1", [id]);
    expect(
        (await policy({ source: "itunes", source_podcast_id: "1" }))
            .disposition,
    ).toBe("blocked");
});

it("applies shared approval and restoration without reviving rejected relationships", async () => {
    const id = await insert();
    const { entity_id } = await policy({ id });
    await pg.exec(
        "INSERT INTO curation_entities(id,kind,label) VALUES('host','comedian','Host')",
    );
    await pg.query(
        "INSERT INTO curation_relationships(id,kind,source_id,target_id,target_kind) VALUES('host-link','host_of','host',$1,'podcast')",
        [entity_id],
    );
    await pg.exec(
        "INSERT INTO curation_decisions(id,relationship_id,version,action,before_state,after_state,actor,reason) VALUES('reject-host','host-link',1,'reject','proposed','rejected','admin','Wrong host')",
    );
    expect((await policy({ id })).disposition).toBe("pending");
    const client = (conn: Pick<PGlite, "query">): SqlClient => ({
        $queryRaw: async <T>(q: Prisma.Sql) =>
            (await conn.query(q.text, q.values)).rows as T,
    });
    const service = createCurationService({
        store: {
            ...client(pg),
            $transaction: (fn) => pg.transaction((tx) => fn(client(tx))),
        },
        adapter: () => podcastAdapter,
        invalidate: async () => {},
    });
    const command = {
        requestId: crypto.randomUUID(),
        target: {
            type: "entity" as const,
            kind: "podcast" as const,
            scope: "entity" as const,
            id: entity_id,
        },
        expectedVersion: 0,
        action: "approve" as const,
        reason: "Verified podcast",
    };
    expect((await service.submit(command, "admin")).status).toBe("applied");
    expect(await allowed(id)).toBe(true);
    await decide(id, "block");
    await decide(id, "restore");
    expect(
        (
            await pg.query<any>(
                "SELECT disposition FROM curation_relationships WHERE id='host-link'",
            )
        ).rows[0].disposition,
    ).toBe("rejected");
    expect(await allowed(id)).toBe(false);
});

it("honors imported provider-only blocks even after compatibility rows disappeared", async () => {
    await pg.exec(
        "INSERT INTO curation_entities(id,kind,label) VALUES('legacy','podcast','Legacy')",
    );
    await pg.exec(
        "INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value) VALUES('old-provider','legacy','podcast','entity','external_id','provider:historicalhash:v1','itunes','777')",
    );
    await pg.exec(
        "INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason) VALUES('legacy-block','legacy',1,'block','pending','blocked','admin','Not a podcast')",
    );
    expect(
        (await policy({ source: "itunes", source_podcast_id: "777" }))
            .disposition,
    ).toBe("blocked");
    await expect(
        insert("itunes", "777", "https://changed.example/feed"),
    ).rejects.toThrow("blocked");
});
it("historical restored deny rows cannot undo a newer durable block", async () => {
    const id = await insert();
    await decide(id, "block");
    await pg.query(
        "INSERT INTO podcast_deny_list(podcast_id,restored_at,restored_by) VALUES($1,now(),'earlier-admin')",
        [id],
    );
    await pg.exec("UPDATE podcast_deny_list SET id=id");
    expect((await policy({ id })).disposition).toBe("blocked");
});
