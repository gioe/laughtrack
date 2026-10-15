import { PGlite } from "@electric-sql/pglite";
import { Prisma } from "@prisma/client";
import { readFileSync } from "node:fs";
import { beforeAll, beforeEach, afterAll, it, expect } from "vitest";
import { createCurationService, type SqlClient, type Store } from "./decisions";
import { clubAdapter } from "./clubAdapter";
let pg: PGlite, store: Store;
const adapter = (conn: Pick<PGlite, "query">): SqlClient => ({
    $queryRaw: async <T>(q: Prisma.Sql) =>
        (await conn.query(q.text, q.values)).rows as T,
});
beforeAll(async () => {
    pg = new PGlite();
    await pg.exec(`CREATE TABLE comedians(id serial PRIMARY KEY,uuid text UNIQUE,name text,visible boolean DEFAULT true,parent_comedian_id int,block_reason text,block_added_by text,block_added_at timestamptz);
 CREATE TABLE clubs(id serial PRIMARY KEY,name text UNIQUE,address text,website text DEFAULT '',city text,state text,country text,google_place_id text,visible boolean DEFAULT true,status text DEFAULT 'active',club_type text DEFAULT 'club');
 CREATE TABLE shows(id serial PRIMARY KEY,name text,club_id int REFERENCES clubs ON DELETE CASCADE,visible boolean DEFAULT true);
 CREATE TABLE podcasts(id int PRIMARY KEY);
 CREATE TABLE lineup_items(show_id int,comedian_id text);
 CREATE TABLE comedian_deny_list(name text PRIMARY KEY);
 CREATE TABLE venue_deny_list(google_place_id text PRIMARY KEY,name text,reason text,added_by text);
 CREATE TABLE club_aliases(id serial PRIMARY KEY,club_id int REFERENCES clubs ON DELETE CASCADE,alias_name text,city text,state text,verified boolean DEFAULT true);
 CREATE TABLE scraping_sources(id serial PRIMARY KEY,club_id int REFERENCES clubs ON DELETE CASCADE,platform text,seatengine_id int,seatengine_v3_id text,ticketmaster_id text,eventbrite_id text,enabled boolean DEFAULT true,comedy_gate_mode text DEFAULT 'enforce',metadata jsonb DEFAULT '{}');`);
    for (const name of [
        "20261012210000_comedian_identity_review",
        "20261014010000_durable_curation_model",
        "20261014190000_comedian_curation_intake",
        "20261015120000_club_curation_intake",
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
async function policy(p = payload(), k: unknown[] = []) {
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
it("holds unreviewed inserts and source-driven publication, retains observations", async () => {
    await pg.exec(
        "INSERT INTO clubs(name,address) VALUES('Unknown','1 Main St') ON CONFLICT(name) DO UPDATE SET visible=true",
    );
    expect((await pg.query("SELECT * FROM clubs")).rows).toHaveLength(0);
    expect(
        (await pg.query("SELECT disposition FROM curation_entities")).rows,
    ).toEqual([{ disposition: "pending" }]);
    expect(
        (await pg.query("SELECT * FROM curation_observations")).rows,
    ).toHaveLength(1);
});
it("scopes same-name venues to location rather than globally merging or blocking", async () => {
    const a = await observe(
        payload({ address: "1 Main St", city: "Boston", state: "MA" }),
    );
    await decision(a, "block");
    const b = await observe(
        payload({ address: "1 Main St", city: "Portland", state: "OR" }),
    );
    expect(b).not.toBe(a);
    expect(
        (
            await policy(
                payload({
                    address: "1 Main St",
                    city: "Portland",
                    state: "OR",
                }),
            )
        ).disposition,
    ).toBe("pending");
});
it("resolves provider IDs, place IDs and aliases and retains keys after public deletion", async () => {
    const p = payload({ google_place_id: "place-1" });
    const c = await approve(p);
    await observe(p, keys);
    await pg.query(
        "INSERT INTO club_aliases(club_id,alias_name,city,state) VALUES($1,'Old Comedy Room','Boston','MA')",
        [c.club_id],
    );
    await decision(c.entity_id, "block");
    expect(
        (await policy(payload({ name: "Renamed", address: "" }), keys))
            .disposition,
    ).toBe("blocked");
    expect(
        (await policy(payload({ name: "Old Comedy Room" }))).disposition,
    ).toBe("blocked");
    await pg.query("DELETE FROM clubs WHERE id=$1", [c.club_id]);
    expect(
        (await policy(payload({ name: "Old Comedy Room" }))).disposition,
    ).toBe("blocked");
    expect((await policy({ id: c.club_id } as any)).disposition).toBe(
        "blocked",
    );
    await pg.query(
        "INSERT INTO clubs(name,address,google_place_id) VALUES($1,$2,$3)",
        ["Renamed", "Other address", "place-1"],
    );
    expect((await pg.query("SELECT * FROM clubs")).rows).toHaveLength(0);
});
it("block hides existing club/show surfaces without changing operating or source policy", async () => {
    const c = await approve();
    await pg.query(
        "INSERT INTO shows(name,club_id) VALUES('Comedy tonight',$1)",
        [c.club_id],
    );
    await pg.query(
        "INSERT INTO scraping_sources(club_id,platform,ticketmaster_id,enabled,comedy_gate_mode) VALUES($1,'ticketmaster','tm-42',true,'enforce')",
        [c.club_id],
    );
    await decision(c.entity_id, "block");
    expect((await pg.query("SELECT visible,status FROM clubs")).rows).toEqual([
        { visible: false, status: "active" },
    ]);
    expect((await pg.query("SELECT visible FROM shows")).rows).toEqual([
        { visible: false },
    ]);
    expect(
        (
            await pg.query(
                "SELECT enabled,comedy_gate_mode FROM scraping_sources",
            )
        ).rows,
    ).toEqual([{ enabled: true, comedy_gate_mode: "enforce" }]);
    await pg.exec(
        "UPDATE clubs SET visible=true; UPDATE shows SET visible=true",
    );
    await pg.query("INSERT INTO shows(name,club_id) VALUES('Retry',$1)", [
        c.club_id,
    ]);
    expect(
        (await pg.query("SELECT * FROM shows WHERE visible")).rows,
    ).toHaveLength(0);
    expect((await pg.query("SELECT * FROM shows")).rows).toHaveLength(1);
});
it("hidden organizer proxies are not rejected, and can route approved shows", async () => {
    const c = await approve(payload({ visible: false }));
    expect((await policy()).disposition).toBe("approved");
    await pg.query(
        "INSERT INTO scraping_sources(club_id,platform,eventbrite_id) VALUES($1,'eventbrite','organizer-42')",
        [c.club_id],
    );
    await pg.query(
        "INSERT INTO shows(name,club_id) VALUES('Routing record',$1)",
        [c.club_id],
    );
    expect(
        (await pg.query("SELECT * FROM scraping_sources")).rows,
    ).toHaveLength(1);
    expect(
        (
            await pg.query(
                "SELECT namespace FROM curation_identity_keys WHERE namespace LIKE 'club-provider:eventbrite%'",
            )
        ).rows,
    ).toHaveLength(0);
});
it("legacy venue denial is durable even when its compatibility row is removed", async () => {
    await pg.exec(
        "INSERT INTO venue_deny_list VALUES('orphan','Excluded venue','Not comedy','admin')",
    );
    expect(
        (await policy(payload({ google_place_id: "orphan" }))).disposition,
    ).toBe("blocked");
    await pg.exec("DELETE FROM venue_deny_list");
    expect(
        (await policy(payload({ google_place_id: "orphan" }))).disposition,
    ).toBe("blocked");
});
it("explicit restore stays pending and preserves disabled sources and show visibility", async () => {
    const c = await approve();
    await pg.query(
        "INSERT INTO scraping_sources(club_id,platform,enabled,comedy_gate_mode) VALUES($1,'ticketmaster',false,'enforce')",
        [c.club_id],
    );
    await decision(c.entity_id, "block");
    await decision(c.entity_id, "restore");
    expect((await policy()).disposition).toBe("pending");
    await pg.exec("UPDATE scraping_sources SET enabled=true");
    expect(
        (
            await pg.query(
                "SELECT enabled,comedy_gate_mode FROM scraping_sources",
            )
        ).rows,
    ).toEqual([{ enabled: false, comedy_gate_mode: "enforce" }]);
    expect((await pg.query("SELECT visible FROM clubs")).rows).toEqual([
        { visible: false },
    ]);
});
it("shared admin approval publishes a candidate without enabling any scraper", async () => {
    const p = payload();
    const id = await observe(p);
    const service = createCurationService({
        store,
        adapter: () => clubAdapter,
        invalidate: async () => {},
    });
    const result = await service.submit(
        {
            requestId: crypto.randomUUID(),
            target: { type: "entity", kind: "club", scope: "entity", id },
            expectedVersion: 0,
            action: "approve",
            reason: "Verified physical venue",
        },
        "admin",
    );
    expect(result.status).toBe("applied");
    expect((await pg.query("SELECT * FROM clubs")).rows).toHaveLength(1);
    expect(
        (await pg.query("SELECT * FROM scraping_sources")).rows,
    ).toHaveLength(0);
});
it("ambiguous identity and unavailable policy never admit", async () => {
    await observe(payload(), keys);
    await observe(payload({ name: "Other", address: "Different address" }));
    const input = payload({ name: "Other", address: "Different address" });
    expect((await policy(input, keys)).disposition).toBe("pending");
    await pg.exec("DELETE FROM curation_intake_lock");
    await expect(observe()).rejects.toThrow(/unavailable/);
    await pg.exec("INSERT INTO curation_intake_lock(id) VALUES(1)");
});

it("deduplicates repeated blocked discovery while retaining new evidence", async () => {
    const id = await observe();
    await decision(id, "block");
    await observe();
    await observe();
    expect(
        (await pg.query("SELECT * FROM curation_entities")).rows,
    ).toHaveLength(1);
    expect(
        (await pg.query("SELECT * FROM curation_observations")).rows,
    ).toHaveLength(1);
    await observe(payload({ website: "https://changed.example.com" }));
    expect(
        (await pg.query("SELECT * FROM curation_observations")).rows,
    ).toHaveLength(2);
    expect((await policy()).disposition).toBe("blocked");
});

it("applies imported blocks to public visibility during rollout", async () => {
    const c = await approve();
    await pg.query(
        "INSERT INTO shows(name,club_id) VALUES('Existing show',$1)",
        [c.club_id],
    );
    await pg.exec(
        "ALTER TABLE curation_decisions DISABLE TRIGGER zz_curation_club_block",
    );
    try {
        await decision(c.entity_id, "block");
    } finally {
        await pg.exec(
            "ALTER TABLE curation_decisions ENABLE TRIGGER zz_curation_club_block",
        );
    }
    expect(
        (await pg.query("SELECT * FROM clubs WHERE visible")).rows,
    ).toHaveLength(1);
    const migration = readFileSync(
        "prisma/migrations/20261015120000_club_curation_intake/migration.sql",
        "utf8",
    );
    await pg.exec(
        migration.slice(migration.indexOf("-- Imported negative decisions")),
    );
    expect(
        (await pg.query("SELECT * FROM clubs WHERE visible")).rows,
    ).toHaveLength(0);
    expect(
        (await pg.query("SELECT * FROM shows WHERE visible")).rows,
    ).toHaveLength(0);
});
it("retains legacy source keys on deletion and rejects explicit reuse of a blocked public ID", async () => {
    const c = await approve();
    await pg.exec(
        "ALTER TABLE scraping_sources DISABLE TRIGGER curation_club_source",
    );
    try {
        await pg.query(
            "INSERT INTO scraping_sources(club_id,ticketmaster_id) VALUES($1,'legacy-tm')",
            [c.club_id],
        );
    } finally {
        await pg.exec(
            "ALTER TABLE scraping_sources ENABLE TRIGGER curation_club_source",
        );
    }
    await decision(c.entity_id, "block");
    await pg.query("DELETE FROM clubs WHERE id=$1", [c.club_id]);
    expect(
        (
            await policy(payload({ name: "Changed", address: "Elsewhere" }), [
                { ...keys[0], value: "legacy-tm" },
            ])
        ).disposition,
    ).toBe("blocked");
    const p = payload({ name: "Different", address: "Elsewhere" });
    await pg.query(
        "SELECT curation_approve_club($1::jsonb,'admin','Verified')",
        [JSON.stringify(p)],
    );
    await pg.query(
        "INSERT INTO clubs(id,name,address,city,state) VALUES($1,$2,$3,$4,$5)",
        [c.club_id, p.name, p.address, p.city, p.state],
    );
    expect((await pg.query("SELECT * FROM clubs")).rows).toHaveLength(0);
});

it("legacy denial blocks the existing approved identity rather than an unbound duplicate", async () => {
    const c = await approve(payload({ google_place_id: "existing-place" }));
    await pg.exec(
        "INSERT INTO venue_deny_list VALUES('existing-place','Comedy Room','Rejected','admin')",
    );
    expect(
        (
            await pg.query(
                "SELECT disposition FROM curation_entities WHERE id=$1",
                [c.entity_id],
            )
        ).rows,
    ).toEqual([{ disposition: "blocked" }]);
    expect(
        (await pg.query("SELECT * FROM clubs WHERE visible")).rows,
    ).toHaveLength(0);
    await pg.exec("DELETE FROM venue_deny_list");
    expect((await policy()).disposition).toBe("blocked");
});

it("allows approved recurring upserts without duplicating the public club", async () => {
    const c = await approve();
    const p = payload();
    const result = await pg.query(
        "INSERT INTO clubs(name,address,city,state,website) VALUES($1,$2,$3,$4,'https://updated.example.com') ON CONFLICT(name) DO UPDATE SET website=EXCLUDED.website RETURNING id,website",
        [p.name, p.address, p.city, p.state],
    );
    expect(result.rows).toEqual([
        { id: c.club_id, website: "https://updated.example.com" },
    ]);
    expect((await pg.query("SELECT * FROM clubs")).rows).toHaveLength(1);
});
