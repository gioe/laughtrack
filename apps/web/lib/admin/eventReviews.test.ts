import { PGlite } from "@electric-sql/pglite";
import { readFileSync } from "node:fs";
import { afterAll, beforeAll, beforeEach, expect, it, vi } from "vitest";
import { Prisma } from "@prisma/client";
const mocks = vi.hoisted(() => ({ raw: vi.fn(), transaction: vi.fn() }));
vi.mock("@/lib/db", () => ({
    db: { $queryRaw: mocks.raw, $transaction: mocks.transaction },
}));
import {
    getEventReview,
    listEventReviews,
    submitEventReview,
} from "./eventReviews";
let pg: PGlite;
function adapter(conn: Pick<PGlite, "query">) {
    return async (
        arg: Prisma.Sql | TemplateStringsArray,
        ...values: unknown[]
    ) => {
        const sql = Array.isArray(arg)
            ? Prisma.sql(arg as TemplateStringsArray, ...values)
            : (arg as Prisma.Sql);
        return (await conn.query(sql.text, sql.values)).rows;
    };
}
beforeAll(async () => {
    pg = new PGlite();
    await pg.exec(`CREATE TABLE scraping_sources(id INTEGER PRIMARY KEY,enabled BOOLEAN DEFAULT true,
 comedy_policy TEXT DEFAULT 'mixed',comedy_policy_version INTEGER DEFAULT 1,comedy_gate_mode TEXT DEFAULT 'enforce',
 comedy_reviewed_by TEXT,comedy_reviewed_at TIMESTAMPTZ,comedy_review_evidence JSONB DEFAULT '{}',scraper_key TEXT DEFAULT 'test');
 CREATE TABLE clubs(id INTEGER PRIMARY KEY,name TEXT); CREATE TABLE shows(id INTEGER PRIMARY KEY,club_id INTEGER REFERENCES clubs(id));
 INSERT INTO scraping_sources(id) VALUES(1);INSERT INTO clubs VALUES(10,'Harvelles');`);
    for (const migration of [
        "20261010223000_add_comedy_eligibility_staging",
        "20261011010000_add_comedy_event_reviews",
        "20261012000000_add_comedy_admin_reviews",
    ])
        await pg.exec(
            readFileSync(
                `prisma/migrations/${migration}/migration.sql`,
                "utf8",
            ),
        );
}, 20000);
afterAll(async () => pg?.close());
beforeEach(async () => {
    await pg.exec(`TRUNCATE comedy_admin_review_requests,comedy_event_reviews,comedy_review_operations,comedy_review_previews,comedy_event_observations,comedy_event_decisions,comedy_event_candidates CASCADE;
    UPDATE scraping_sources SET enabled=true,comedy_gate_mode='enforce',comedy_policy_version=1;
    INSERT INTO comedy_event_candidates(id,source_id,event_key,club_id) VALUES(1,1,'native:1',10);
    INSERT INTO comedy_event_decisions(id,candidate_id,payload_fingerprint,identity_fingerprint,policy_version,classifier_version,gate_mode,decision,payload,evidence)
    VALUES(1,1,'payload','identity',1,'rules','enforce','review','{"name":"Comedy Night","date":"2026-11-01T20:00:00Z"}','{"performers":[]}');
    INSERT INTO comedy_event_observations(candidate_id,generation,decision_id,baseline_identity_fingerprint) VALUES(1,1,1,'identity');`);
    mocks.raw.mockImplementation(adapter(pg));
    mocks.transaction.mockImplementation((fn) =>
        pg.transaction((tx) => fn({ $queryRaw: adapter(tx) })),
    );
});
const id = "10000000-0000-4000-8000-000000000001";
async function submission() {
    const detail = await getEventReview(1);
    return {
        id,
        candidateId: 1,
        token: detail!.current.token,
        action: "approve" as const,
        reason: "Explicit comedy billing",
    };
}
it("reads evidence and mode with literal search, stable pagination and history", async () => {
    const page = await listEventReviews({ q: "harvelles" });
    expect(page.items).toHaveLength(1);
    expect(page.ceiling).toBe(1);
    expect(page.next).toBeNull();
    expect(page.items[0].observation_generation).toBe("1");
    expect((await listEventReviews({ q: "' OR 1=1 --" })).items).toHaveLength(
        0,
    );
    expect((await listEventReviews({ mode: "off" })).items).toHaveLength(0);
    expect((await getEventReview(1))!.observations).toHaveLength(1);
    expect(await getEventReview(999)).toBeNull();
});
it("records only a pending attributed command; retries are idempotent even after apply", async () => {
    const input = await submission();
    const first = await submitEventReview(input, "admin");
    expect(first.status).toBe("pending");
    expect(first.actor).toBe("admin");
    expect(await submitEventReview(input, "admin")).toEqual(first);
    expect(
        (await pg.query("SELECT * FROM comedy_event_reviews")).rows,
    ).toHaveLength(0);
    await pg.exec("UPDATE comedy_admin_review_requests SET status='applied'");
    expect((await submitEventReview(input, "admin")).status).toBe("applied");
    await expect(
        submitEventReview({ ...input, action: "reject" }, "admin"),
    ).rejects.toThrow("different decision");
    await expect(submitEventReview(input, "someone-else")).rejects.toThrow(
        "different decision",
    );
});
it("rejects stale generation, review version, policy, disabled and off sources", async () => {
    const input = await submission();
    for (const update of [
        "UPDATE comedy_event_candidates SET observation_generation=2",
        "UPDATE comedy_event_candidates SET review_version=1",
        "UPDATE scraping_sources SET comedy_policy_version=2",
        "UPDATE scraping_sources SET comedy_gate_mode='off'",
        "UPDATE scraping_sources SET enabled=false",
    ]) {
        await pg.exec(update);
        await expect(submitEventReview(input, "admin")).rejects.toThrow(
            "changed",
        );
        await pg.exec(
            "UPDATE comedy_event_candidates SET observation_generation=1,review_version=0; UPDATE scraping_sources SET comedy_policy_version=1,comedy_gate_mode='enforce',enabled=true",
        );
    }
    expect(
        (await pg.query("SELECT * FROM comedy_admin_review_requests")).rows,
    ).toHaveLength(0);
});
it("allows only one pending request per candidate", async () => {
    const input = await submission();
    await submitEventReview(input, "admin");
    await expect(
        submitEventReview(
            { ...input, id: "20000000-0000-4000-8000-000000000001" },
            "admin",
        ),
    ).rejects.toThrow("pending review");
});
it("paginates without bringing later candidates into the captured ceiling", async () => {
    await pg.exec(
        "INSERT INTO comedy_event_candidates(id,source_id,event_key,club_id) SELECT n,1,'native:'||n,10 FROM generate_series(2,52) n",
    );
    const first = await listEventReviews({});
    expect(first.items).toHaveLength(50);
    expect(first.next).toBe(50);
    expect(first.ceiling).toBe(52);
    await pg.exec(
        "INSERT INTO comedy_event_candidates(id,source_id,event_key,club_id) VALUES(53,1,'native:53',10)",
    );
    const second = await listEventReviews({
        after: first.next!,
        ceiling: first.ceiling,
    });
    expect(second.items.map((r) => r.candidate_id)).toEqual([51, 52]);
    expect(second.next).toBeNull();
});

import { listReviews, getReview, decideReview } from "./reviews";
it("adapts event evidence and queues an idempotent deferred decision through the shared inbox", async () => {
    const page = await listReviews({ workflow: "event_eligibility" });
    expect(page.total).toBeNull();
    expect(page.cursor).toEqual({ ceiling: 1, next: null });
    const detail = (await getReview("event_eligibility", "1"))!;
    expect(detail.actions).toEqual(["approve", "reject", "defer"]);
    expect(
        detail.evidence.some((e) => e.title === "Lineup and parent identities"),
    ).toBe(true);
    const input = {
        workflow: "event_eligibility" as const,
        id: "1",
        requestId: id,
        token: detail.token,
        action: "defer" as const,
        reason: "Need venue evidence",
    };
    expect(await decideReview(input, "admin")).toMatchObject({
        status: "pending",
    });
    expect(await decideReview(input, "admin")).toMatchObject({
        status: "pending",
    });
    const pending = (await getReview("event_eligibility", "1"))!;
    expect(pending.processing).toBe(true);
    expect(pending.actions).toEqual([]);
    expect(pending.history).toEqual(
        expect.arrayContaining([
            expect.objectContaining({
                action: "defer",
                actor: "admin",
                status: "pending",
            }),
        ]),
    );
    expect(
        (await pg.query("SELECT * FROM comedy_event_reviews")).rows,
    ).toHaveLength(0);
    expect(
        (await pg.query("SELECT * FROM comedy_admin_review_requests")).rows,
    ).toHaveLength(1);
    await expect(
        decideReview({ ...input, reason: "Changed reason" }, "admin"),
    ).rejects.toThrow("different decision");
});
it("preserves event scope checks and rejects unsupported workflow actions", async () => {
    const input = await submission();
    const shared = {
        workflow: "event_eligibility" as const,
        id: "1",
        requestId: id,
        token: input.token,
        action: input.action,
        reason: input.reason,
    };
    await expect(
        decideReview({ ...shared, action: "link" }, "admin"),
    ).rejects.toThrow("Invalid action");
    await expect(
        decideReview({ ...shared, reason: " " }, "admin"),
    ).rejects.toThrow();
    await expect(
        listReviews({ workflow: "event_eligibility", status: "pending" }),
    ).rejects.toThrow("Invalid status");
    await expect(
        decideReview(
            { ...shared, workflow: "podcast_association", action: "defer" },
            "admin",
        ),
    ).rejects.toThrow("Invalid action");
    for (const update of [
        "UPDATE scraping_sources SET enabled=false",
        "UPDATE scraping_sources SET comedy_gate_mode='off'",
        "UPDATE scraping_sources SET comedy_policy_version=2",
    ]) {
        await pg.exec(update);
        expect((await getReview("event_eligibility", "1"))!.actions).toEqual(
            [],
        );
        await expect(decideReview(shared, "admin")).rejects.toThrow("changed");
        await pg.exec(
            "UPDATE scraping_sources SET enabled=true,comedy_gate_mode='enforce',comedy_policy_version=1",
        );
    }
});
