import { PGlite } from "@electric-sql/pglite";
import { Prisma } from "@prisma/client";
import { readFileSync } from "node:fs";
import { beforeAll, beforeEach, afterAll, it, expect } from "vitest";
import { createCurationService, type SqlClient, type Store } from "./decisions";
import { showAdapter } from "./showAdapter";
let pg: PGlite, store: Store;
const adapter = (conn: Pick<PGlite, "query">): SqlClient => ({
    $queryRaw: async <T>(q: Prisma.Sql) =>
        (await conn.query(q.text, q.values)).rows as T,
});
beforeAll(async () => {
    pg = new PGlite();
    await pg.exec(`CREATE TABLE comedians(id serial PRIMARY KEY,uuid text UNIQUE,name text,visible boolean DEFAULT true,parent_comedian_id int,block_reason text,block_added_by text,block_added_at timestamptz);
 CREATE TABLE clubs(id serial PRIMARY KEY,name text UNIQUE,address text,website text DEFAULT '',city text,state text,country text,google_place_id text,visible boolean DEFAULT true,status text DEFAULT 'active',club_type text DEFAULT 'club');
 CREATE TABLE shows(id serial PRIMARY KEY,name text,club_id int REFERENCES clubs ON DELETE CASCADE,date timestamptz NOT NULL, room text, show_page_url text, source_performance_id text, is_cancelled boolean DEFAULT false);
 CREATE TABLE podcasts(id int PRIMARY KEY);
 CREATE TABLE lineup_items(show_id int,comedian_id text);
 CREATE TABLE comedian_deny_list(name text PRIMARY KEY);
 CREATE TABLE venue_deny_list(google_place_id text PRIMARY KEY,name text,reason text,added_by text);
 CREATE TABLE club_aliases(id serial PRIMARY KEY,club_id int REFERENCES clubs ON DELETE CASCADE,alias_name text,city text,state text,verified boolean DEFAULT true);
 CREATE TABLE scraping_sources(id serial PRIMARY KEY,club_id int REFERENCES clubs ON DELETE CASCADE,platform text,seatengine_id int,seatengine_v3_id text,ticketmaster_id text,eventbrite_id text,enabled boolean DEFAULT true,comedy_gate_mode text DEFAULT 'enforce',metadata jsonb DEFAULT '{}');`);
    for (const name of [
        "20261010223000_add_comedy_eligibility_staging",
        "20261011010000_add_comedy_event_reviews",
        "20261012210000_comedian_identity_review",
        "20261014010000_durable_curation_model",
        "20261014190000_comedian_curation_intake",
        "20261015110000_show_publication_visibility",
        "20261015120000_club_curation_intake",
        "20261015180000_show_curation_intake",
    ])
        await pg.exec(
            readFileSync(`prisma/migrations/${name}/migration.sql`, "utf8"),
        );
    store = {
        ...adapter(pg),
        $transaction: (fn) => pg.transaction((tx) => fn(adapter(tx))),
    };
}, 30000);
afterAll(async () => pg.close());
beforeEach(async () => {
    await pg.exec(
        "TRUNCATE curation_entities,clubs,shows,scraping_sources,club_aliases,venue_deny_list CASCADE",
    );
});
const payload = (extra = {}) => ({
    name: "Comedy Room",
    address: "1 Main St, Boston, MA",
    city: "Boston",
    state: "MA",
    website: "https://example.com",
    ...extra,
});
const keys = [
    {
        namespace: "club-provider:ticketmaster_id:v1",
        scope: "global",
        value: "tm-42",
    },
];
async function policy(
    p: Record<string, unknown> = payload(),
    k: unknown[] = [],
) {
    return (
        await pg.query<any>(
            "SELECT * FROM curation_club_policy($1::jsonb,$2::jsonb)",
            [JSON.stringify(p), JSON.stringify(k)],
        )
    ).rows[0];
}
async function observe(p = payload(), k: unknown[] = []) {
    return (
        await pg.query<any>(
            "SELECT curation_observe_club($1::jsonb,$2::jsonb) id",
            [JSON.stringify(p), JSON.stringify(k)],
        )
    ).rows[0].id as string;
}
async function approve(p = payload()) {
    await pg.query(
        "SELECT curation_approve_club($1::jsonb,'admin','Verified venue')",
        [JSON.stringify(p)],
    );
    await pg.query(
        "INSERT INTO clubs(name,address,website,city,state,country,google_place_id,visible) VALUES($1,$2,$3,$4,$5,$6,$7,$8)",
        [
            p.name,
            p.address,
            p.website,
            p.city,
            p.state,
            (p as any).country ?? null,
            (p as any).google_place_id ?? null,
            (p as any).visible ?? true,
        ],
    );
    return policy(p);
}
async function decision(id: string, action: string) {
    await pg.query(
        `INSERT INTO curation_decisions(id,entity_id,version,action,before_state,after_state,actor,reason) SELECT gen_random_uuid()::text,id,version+1,$2,disposition,CASE $2 WHEN 'block' THEN 'blocked' WHEN 'restore' THEN 'pending' ELSE 'approved' END,'admin','Reviewed' FROM curation_entities WHERE id=$1`,
        [id, action],
    );
}

async function setup() {
    const c = await approve();
    const source = (
        await pg.query<any>(
            "INSERT INTO scraping_sources(club_id,platform) VALUES($1,'test') RETURNING id",
            [c.club_id],
        )
    ).rows[0].id;
    return {
        club_id: c.club_id,
        source_id: source,
        name: "Same title",
        date: "2027-01-01T20:00:00Z",
        source_performance_id: "provider:1",
        url: "https://example.com/event/1",
    };
}
async function observeShow(p: any) {
    return (
        await pg.query<any>("SELECT curation_observe_show($1::jsonb) id", [
            JSON.stringify(p),
        ])
    ).rows[0].id;
}
async function showPolicy(p: any) {
    return (
        await pg.query<any>("SELECT * FROM curation_show_policy($1::jsonb)", [
            JSON.stringify(p),
        ])
    ).rows[0];
}
async function publish(p: any) {
    return (
        await pg.query<any>(
            "INSERT INTO shows(name,club_id,date,room,show_page_url,source_performance_id) VALUES($1,$2,$3,$4,$5,$6) RETURNING id",
            [
                p.name,
                p.club_id,
                p.date,
                p.room ?? null,
                p.url,
                p.source_performance_id ?? null,
            ],
        )
    ).rows[0]?.id;
}
it("blocks native occurrences through renamed, moved and rescheduled rediscovery without banning titles", async () => {
    const p = await setup();
    const id = await observeShow(p);
    await decision(id, "block");
    expect(
        (
            await showPolicy({
                ...p,
                name: "New title",
                url: "https://other.test",
                date: "2028-01-01",
            })
        ).allowed,
    ).toBe(false);
    expect(await publish({ ...p, date: "2028-01-01" })).toBeUndefined();
    expect(
        await publish({ ...p, source_performance_id: "provider:2" }),
    ).toBeTypeOf("number");
});
it("retains provider URL IDs and source ownership independently of title", async () => {
    const p = await setup();
    const input = {
        ...p,
        source_performance_id: null,
        url: "https://www.eventbrite.com/e/old-tickets-12345",
        event_key: "provider:12345",
    };
    const id = await observeShow(input);
    await decision(id, "block");
    expect(
        (
            await showPolicy({
                ...input,
                date: "2028-01-01",
                url: "https://www.eventbrite.com/e/new-tickets-12345",
                event_key: "changed",
            })
        ).allowed,
    ).toBe(false);
    expect(
        (
            await showPolicy({
                ...input,
                date: "2028-01-01",
                url: "https://example.com",
                source_id: 999,
            })
        ).allowed,
    ).toBe(true);
});
it("suppresses public rows while retaining references and requiring explicit restoration", async () => {
    const p = await setup();
    const show = await publish(p);
    const id = await observeShow({ ...p, id: show });
    await pg.exec(
        "CREATE TABLE saved_test(show_id int REFERENCES shows(id)); CREATE TABLE ticket_test(show_id int REFERENCES shows(id))",
    );
    await pg.query("INSERT INTO saved_test VALUES($1)", [show]);
    await pg.query("INSERT INTO ticket_test VALUES($1)", [show]);
    await decision(id, "block");
    await pg.query("DELETE FROM shows WHERE id=$1", [show]);
    expect((await pg.query("SELECT visible FROM shows")).rows).toEqual([
        { visible: false },
    ]);
    expect((await pg.query("SELECT * FROM saved_test")).rows).toHaveLength(1);
    await decision(id, "restore");
    expect((await showPolicy(p)).allowed).toBe(false);
    await decision(id, "approve");
    expect((await showPolicy(p)).allowed).toBe(true);
    expect((await pg.query("SELECT visible FROM shows")).rows).toEqual([
        { visible: false },
    ]);
    await pg.exec("DROP TABLE saved_test; DROP TABLE ticket_test");
});
it("blocks only an explicit source-owned series, including future members", async () => {
    const p = await setup();
    const a = await publish(p);
    await observeShow({ ...p, id: a, series_id: "series-1" });
    const b = await publish({ ...p, source_performance_id: "provider:2" });
    const series = (
        await pg.query<any>(
            "SELECT id FROM curation_entities WHERE identity_scope='series'",
        )
    ).rows[0].id;
    await decision(series, "block");
    expect((await pg.query("SELECT id FROM shows WHERE visible")).rows).toEqual(
        [{ id: b }],
    );
    const future = {
        ...p,
        source_performance_id: "provider:3",
        series_id: "series-1",
    };
    await observeShow(future);
    expect(await publish(future)).toBeUndefined();
    const existing = {
        ...p,
        source_performance_id: "provider:2",
        id: b,
        series_id: "series-1",
    };
    await observeShow(existing);
    expect((await pg.query("SELECT id FROM shows WHERE visible")).rows).toEqual(
        [],
    );
    await decision(series, "restore");
    expect((await pg.query("SELECT id FROM shows WHERE visible")).rows).toEqual(
        [],
    );
});
it("propagates a block over confirmed cross-source mappings", async () => {
    const p = await setup();
    const a = await observeShow(p);
    const q = { ...p, source_performance_id: "other:9", date: "2028-01-01" };
    const b = await observeShow(q);
    await decision(a, "block");
    await pg.query("INSERT INTO curation_show_mappings VALUES($1,$2,$3)", [
        ...[a, b].sort(),
        JSON.stringify({ verified: true }),
    ]);
    expect((await showPolicy(q)).allowed).toBe(false);
});
it("shared preview reports occurrence scope and affected events; refuses unidentified series", async () => {
    const p = await setup();
    const show = await publish(p);
    const id = await observeShow({ ...p, id: show });
    const service = createCurationService({
        store,
        adapter: () => showAdapter,
        invalidate: async () => {},
    });
    const command = {
        requestId: crypto.randomUUID(),
        target: {
            type: "entity" as const,
            kind: "show" as const,
            scope: "entity" as const,
            id,
        },
        expectedVersion: 0,
        action: "block" as const,
        reason: "Not a comedy show",
    };
    const preview = await service.preview(command);
    expect(JSON.stringify(preview)).toContain("One occurrence");
    expect(JSON.stringify(preview)).toContain("Known affected events (1)");
    expect((await service.submit(command, "admin")).status).toBe("applied");
    await pg.exec(
        "INSERT INTO curation_entities(id,kind,identity_scope,label) VALUES('unknown-series','show','series','Same title')",
    );
    await expect(
        service.submit(
            {
                ...command,
                requestId: crypto.randomUUID(),
                target: {
                    ...command.target,
                    id: "unknown-series",
                    scope: "series",
                },
            },
            "admin",
        ),
    ).rejects.toThrow(/source-owned/);
});

it("an applied event rejection creates a durable occurrence block despite changed evidence", async () => {
    const p = await setup();
    const show = await publish(p);
    const c = (
        await pg.query<any>(
            "INSERT INTO comedy_event_candidates(source_id,event_key,club_id) VALUES($1,'provider:event-1',$2) RETURNING id",
            [p.source_id, p.club_id],
        )
    ).rows[0].id;
    const d = (
        await pg.query<any>(
            "INSERT INTO comedy_event_decisions(candidate_id,payload_fingerprint,identity_fingerprint,policy_version,classifier_version,gate_mode,decision,payload,evidence) VALUES($1,'p','i',1,'v1','enforce','review',$2,'{}') RETURNING id",
            [c, JSON.stringify(p)],
        )
    ).rows[0].id;
    await pg.query(
        "INSERT INTO comedy_event_publications(candidate_id,decision_id,show_id) VALUES($1,$2,$3)",
        [c, d, show],
    );
    await pg.query(
        "INSERT INTO comedy_event_observations(candidate_id,generation,decision_id,baseline_identity_fingerprint) VALUES($1,1,$2,'i')",
        [c, d],
    );
    await pg.exec(
        "INSERT INTO comedy_review_previews(id,actor,action,reason,items,token_digest,expires_at) VALUES('preview','admin','reject','Not comedy','[{}]','token',now()+interval '1 hour'); INSERT INTO comedy_review_operations(idempotency_key,preview_id,actor,token_digest,result) VALUES('operation','preview','admin','token','{}')",
    );
    await pg.query(
        "INSERT INTO comedy_event_reviews(candidate_id,observation_generation,decision_id,review_version,payload_fingerprint,identity_fingerprint,policy_version,actor,reason,action,operation_key) VALUES($1,1,$2,1,'p','i',1,'admin','Not comedy','reject','operation')",
        [c, d],
    );
    expect((await pg.query("SELECT visible FROM shows")).rows).toEqual([
        { visible: false },
    ]);
    await pg.query(
        "INSERT INTO comedy_event_decisions(candidate_id,payload_fingerprint,identity_fingerprint,policy_version,classifier_version,gate_mode,decision,payload,evidence) VALUES($1,'changed','new-identity',2,'v2','enforce','accept',$2,'{}')",
        [
            c,
            JSON.stringify({
                ...p,
                name: "Comedy!",
                date: "2028-01-01",
                url: "https://changed.test",
            }),
        ],
    );
    expect((await showPolicy(p)).allowed).toBe(false);
    expect(
        (
            await pg.query(
                "SELECT action FROM curation_decisions WHERE entity_id IN (SELECT id FROM curation_entities WHERE kind='show')",
            )
        ).rows,
    ).toEqual([{ action: "block" }]);
});
it("stable raw provider IDs survive all presentation-field edits", async () => {
    const p = {
        ...(await setup()),
        source_performance_id: null,
        provider_event_id: "ticketmaster:raw123",
    };
    await decision(await observeShow(p), "block");
    expect(
        (
            await showPolicy({
                ...p,
                name: "Changed",
                date: "2028-01-01",
                url: "https://different.test",
            })
        ).allowed,
    ).toBe(false);
});
it("restoring an occurrence does not override an independent series block", async () => {
    const p = { ...(await setup()), series_id: "series" };
    const id = await observeShow(p);
    const series = (
        await pg.query<any>(
            "SELECT id FROM curation_entities WHERE identity_scope='series'",
        )
    ).rows[0].id;
    await decision(id, "block");
    await decision(series, "block");
    await decision(id, "restore");
    await decision(id, "approve");
    expect((await showPolicy(p)).allowed).toBe(false);
});

it("advances the public cache revision when a worker or direct decision suppresses a show", async () => {
    const p = await setup();
    const show = await publish(p);
    const id = await observeShow({ ...p, id: show });
    const before = (
        await pg.query<any>("SELECT revision FROM show_publication_revision")
    ).rows[0].revision;
    await decision(id, "block");
    const after = (
        await pg.query<any>("SELECT revision FROM show_publication_revision")
    ).rows[0].revision;
    expect(Number(after)).toBeGreaterThan(Number(before));
});
