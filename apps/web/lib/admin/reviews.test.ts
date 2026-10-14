import { PGlite } from "@electric-sql/pglite";
import { readFileSync } from "node:fs";
import { afterAll, beforeAll, beforeEach, expect, it, vi } from "vitest";
import { Prisma } from "@prisma/client";
const mocks = vi.hoisted(() => ({ raw: vi.fn(), transaction: vi.fn() }));
vi.mock("@/lib/db", () => ({
    db: { $queryRaw: mocks.raw, $transaction: mocks.transaction },
}));
import {
    listReviews,
    getReview,
    decideReview,
    undoReview,
    searchReviewComedians,
} from "./reviews";
let pg: PGlite;
function adapter(conn: Pick<PGlite, "query">) {
    return async (
        arg: Prisma.Sql | TemplateStringsArray,
        ...values: unknown[]
    ) => {
        const sql = Array.isArray(arg)
            ? Prisma.sql(arg as TemplateStringsArray, ...values)
            : (arg as Prisma.Sql);
        if (
            sql.text.includes("SELECT curation_approve_comedian") ||
            sql.text.includes("SELECT curation_observe_comedian") ||
            sql.text.includes("SELECT curation_reopen_comedian") ||
            sql.text.includes("SELECT e.version FROM curation_entities")
        )
            return [];
        return (await conn.query(sql.text, sql.values)).rows;
    };
}
beforeAll(async () => {
    pg = new PGlite();
    await pg.exec(`CREATE TABLE comedians(id serial PRIMARY KEY,uuid text UNIQUE,name text,visible boolean DEFAULT true,parent_comedian_id int,total_shows int DEFAULT 0,block_reason text,block_added_by text,block_added_at timestamptz);
 CREATE TABLE shows(id serial PRIMARY KEY,name text,date timestamptz);
 CREATE TABLE lineup_items(show_id int REFERENCES shows(id),comedian_id text REFERENCES comedians(uuid),UNIQUE(show_id,comedian_id));
 CREATE TABLE comedian_deny_list(name text);
 CREATE TABLE podcasts(id serial PRIMARY KEY,title text,website_url text);
 CREATE TABLE podcast_deny_list(id serial PRIMARY KEY,podcast_id int);
 CREATE TABLE comedian_podcasts(id serial PRIMARY KEY,comedian_id int REFERENCES comedians(id),podcast_id int REFERENCES podcasts(id),association_type text,source text,review_status text DEFAULT 'pending',confidence float,evidence jsonb,reviewed_at timestamptz,reviewed_by text,created_at timestamptz DEFAULT now(),updated_at timestamptz DEFAULT now());`);
    const migration = readFileSync(
        "prisma/migrations/20261012210000_comedian_identity_review/migration.sql",
        "utf8",
    );
    await pg.exec(migration);
    await pg.exec(migration);
}, 30000);
afterAll(async () => pg?.close());
beforeEach(async () => {
    await pg.exec(`TRUNCATE comedians,shows,lineup_items,comedian_deny_list,podcasts,podcast_deny_list,comedian_podcasts,comedian_identity_candidates,comedian_identity_evidence,admin_review_decisions RESTART IDENTITY CASCADE;
 INSERT INTO shows(id,name,date) VALUES(1,'Friday comedy',now()+interval '1 day'),(2,'Another show',now()+interval '2 days');
 INSERT INTO comedian_identity_candidates(uuid,name) VALUES('candidate','New Person');
 INSERT INTO comedian_identity_evidence(fingerprint,candidate_uuid,show_id,source_url,source_key,extraction_kind,raw_name,context) VALUES('e1','candidate',1,'https://example.com/show','test','extracted_lineup','New Person','Featuring New Person');`);
    mocks.raw.mockImplementation(adapter(pg));
    mocks.transaction.mockImplementation((fn) =>
        pg.transaction((tx) => fn({ $queryRaw: adapter(tx) })),
    );
});
async function decision(
    action: "approve" | "reject" | "link" = "approve",
    extra = {},
) {
    return {
        workflow: "comedian_identity" as const,
        id: "candidate",
        token: (await getReview("comedian_identity", "candidate"))!.token,
        action,
        reason: "Reviewed performer evidence",
        ...extra,
    };
}
it("stages without creating public comedians, and searches literally", async () => {
    expect((await listReviews({})).total).toBe(1);
    expect((await pg.query("SELECT * FROM comedians")).rows).toHaveLength(0);
    expect((await listReviews({ q: "' OR 1=1 --" })).total).toBe(0);
    expect(await searchReviewComedians("' OR 1=1 --")).toEqual([]);
    expect(
        (await getReview("comedian_identity", "candidate"))!.evidence[0].showId,
    ).toBe(1);
});
it("approves only selected appearances and audits the decision", async () => {
    const result = await decideReview(
        await decision("approve", { showIds: [1, 2] }),
        "admin",
    );
    expect((await pg.query("SELECT * FROM lineup_items")).rows).toHaveLength(1);
    expect((await getReview("comedian_identity", "candidate"))!.status).toBe(
        "accepted",
    );
    expect(
        (await pg.query("SELECT identity_validated_by FROM comedians")).rows[0],
    ).toEqual({ identity_validated_by: "admin" });
    expect(result.decisionId).toBeTruthy();
});
it("identity approval alone creates no appearances", async () => {
    await decideReview(await decision(), "admin");
    expect((await pg.query("SELECT * FROM lineup_items")).rows).toHaveLength(0);
});
it("rejects stale decisions and rolls back a duplicate approval", async () => {
    const input = await decision();
    await decideReview(input, "admin");
    await expect(decideReview(input, "admin")).rejects.toThrow("changed");
    expect(
        (await pg.query("SELECT * FROM admin_review_decisions")).rows,
    ).toHaveLength(1);
});
it("links an existing canonical identity without inserting another", async () => {
    await pg.exec(
        "INSERT INTO comedians(id,uuid,name) VALUES(9,'existing','New Person')",
    );
    await decideReview(
        await decision("link", { targetId: 9, showIds: [1] }),
        "admin",
    );
    expect((await pg.query("SELECT * FROM comedians")).rows).toHaveLength(1);
    expect(
        (await pg.query("SELECT comedian_id FROM lineup_items")).rows[0],
    ).toEqual({ comedian_id: "existing" });
});
it("refuses hidden and denied canonical targets", async () => {
    await pg.exec(
        "INSERT INTO comedians(id,uuid,name,visible) VALUES(9,'existing','New Person',false)",
    );
    await expect(
        decideReview(await decision("link", { targetId: 9 }), "admin"),
    ).rejects.toThrow("active canonical");
    await pg.exec(
        "UPDATE comedians SET visible=true; INSERT INTO comedian_deny_list VALUES('New Person')",
    );
    await expect(
        decideReview(await decision("link", { targetId: 9 }), "admin"),
    ).rejects.toThrow("denied");
    expect((await getReview("comedian_identity", "candidate"))!.status).toBe(
        "pending",
    );
});
it("undo restores pending while retaining an attributed history", async () => {
    const { decisionId } = await decideReview(
        await decision("approve", { showIds: [1] }),
        "admin",
    );
    await undoReview(decisionId!, "admin");
    expect((await getReview("comedian_identity", "candidate"))!.status).toBe(
        "pending",
    );
    expect(
        (await pg.query("SELECT visible,identity_validated_at FROM comedians"))
            .rows[0],
    ).toEqual({ visible: false, identity_validated_at: null });
    expect((await pg.query("SELECT * FROM lineup_items")).rows).toHaveLength(0);
    expect(
        (await getReview("comedian_identity", "candidate"))!.history[0].undone,
    ).toBe(true);
    await expect(undoReview(decisionId!, "admin")).rejects.toThrow(
        "cannot be undone",
    );
});
it("undo does not remove pre-existing appearances", async () => {
    await pg.exec(
        "INSERT INTO comedians(id,uuid,name) VALUES(9,'existing','New Person'); INSERT INTO lineup_items VALUES(1,'existing')",
    );
    const { decisionId } = await decideReview(
        await decision("link", { targetId: 9, showIds: [1] }),
        "admin",
    );
    await undoReview(decisionId!, "admin");
    expect((await pg.query("SELECT * FROM lineup_items")).rows).toHaveLength(1);
});
it("undo refuses later identity changes and another reviewer's request", async () => {
    const { decisionId } = await decideReview(await decision(), "admin");
    await expect(undoReview(decisionId!, "other")).rejects.toThrow(
        "cannot be undone",
    );
    await pg.exec("UPDATE comedians SET name='Updated name'");
    await expect(undoReview(decisionId!, "admin")).rejects.toThrow("changed");
});
it("podcast adapter approves only a relationship and supports undo", async () => {
    await pg.exec(
        "INSERT INTO comedians(id,uuid,name) VALUES(9,'existing','New Person'); INSERT INTO podcasts(id,title) VALUES(5,'A podcast'); INSERT INTO comedian_podcasts(id,comedian_id,podcast_id,association_type,source,evidence) VALUES(3,9,5,'host','test','{}')",
    );
    expect((await listReviews({ workflow: "podcast_association" })).total).toBe(
        1,
    );
    const item = (await getReview("podcast_association", "3"))!;
    const { decisionId } = await decideReview(
        {
            workflow: item.workflow,
            id: item.id,
            token: item.token,
            action: "approve",
            reason: "Checked credits",
        },
        "admin",
    );
    expect((await getReview(item.workflow, item.id))!.status).toBe("accepted");
    expect(
        (await pg.query("SELECT identity_validated_at FROM comedians")).rows[0],
    ).toEqual({ identity_validated_at: null });
    await undoReview(decisionId!, "admin");
    expect((await getReview(item.workflow, item.id))!.status).toBe("pending");
});

it("allows a reviewer to approve again after undoing creation", async () => {
    const { decisionId } = await decideReview(await decision(), "admin");
    await undoReview(decisionId!, "admin");
    await decideReview(await decision(), "admin");
    expect((await pg.query("SELECT visible FROM comedians")).rows).toEqual([
        { visible: true },
    ]);
});

it("suggests existing canonical names contained in decorated source names", async () => {
    await pg.exec(
        "INSERT INTO comedians(uuid,name) VALUES('steve','Steve Marshall')",
    );
    expect(await searchReviewComedians("Steve Marshall Comedy")).toEqual([
        { id: 1, name: "Steve Marshall" },
    ]);
});
