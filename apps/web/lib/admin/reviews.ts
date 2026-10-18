import {
    eventReviewFilters,
    EventReviewConflict,
    submitEventReview,
} from "./eventReviews";
import { listEventInbox, getEventInbox } from "./eventReviewAdapter";
import { reviewDefinitions, type ReviewResult } from "./reviewTypes";
import { createHash, randomUUID } from "node:crypto";
import { Prisma } from "@prisma/client";
import { z } from "zod";
import { db } from "@/lib/db";
import {
    reviewWorkflows,
    type ReviewItem,
    type ReviewPage,
    type ReviewWorkflow,
} from "./reviewTypes";

type Tx = Pick<Prisma.TransactionClient, "$queryRaw">;
type Row = Record<string, any>;
import { ReviewConflict } from "./reviewErrors";
export { ReviewConflict } from "./reviewErrors";
import {
    listVisibilityReviews,
    getVisibilityReview,
    decideVisibilityReview,
} from "./visibilityReviews";
export const reviewFilters = z.object({
    workflow: z.enum(reviewWorkflows).default("comedian_identity"),
    status: z
        .enum([
            "pending",
            "accepted",
            "rejected",
            "all",
            "active",
            "blocked",
            "review",
            "accept",
            "approve",
            "reject",
            "defer",
            "stale_review",
            "stale_policy",
            "awaiting_observation",
        ])
        .optional(),
    source: z.coerce.number().int().positive().max(2147483647).optional(),
    mode: z.enum(["off", "shadow", "enforce"]).optional(),
    after: z.coerce.number().int().nonnegative().max(2147483647).default(0),
    ceiling: z.coerce.number().int().nonnegative().max(2147483647).optional(),
    q: z.string().trim().max(200).default(""),
    page: z.coerce.number().int().min(1).max(100000).default(1),
});
export const reviewSubmission = z
    .object({
        workflow: z.enum(reviewWorkflows),
        id: z.string().min(1).max(100),
        token: z.string().regex(/^[a-f0-9]{64}$/),
        action: z.enum([
            "approve",
            "link",
            "reject",
            "defer",
            "block",
            "unblock",
        ]),
        requestId: z.string().uuid().optional(),
        name: z.string().trim().min(1).max(200).optional(),
        targetId: z.number().int().positive().optional(),
        showIds: z.array(z.number().int().positive()).max(100).default([]),
        reason: z.string().trim().min(1).max(2000),
    })
    .strict();
const plain = <T>(value: T): T => JSON.parse(JSON.stringify(value));
function token(row: Row) {
    const stable = (value: any): any =>
        Array.isArray(value)
            ? value.map(stable)
            : value && typeof value === "object"
              ? Object.fromEntries(
                    Object.keys(value)
                        .sort()
                        .map((k) => [k, stable(value[k])]),
                )
              : value;
    return createHash("sha256")
        .update(JSON.stringify(stable(plain(row))))
        .digest("hex");
}
const candidateColumns = Prisma.sql`uuid,name,status,version,canonical_comedian_id,reviewed_by,reviewed_at,reason`;
const associationColumns = Prisma.sql`id,comedian_id,podcast_id,association_type,source,review_status,confidence,evidence,reviewed_at,reviewed_by,updated_at`;
async function current(
    tx: Tx,
    workflow: ReviewWorkflow,
    id: string,
    lock = false,
): Promise<Row | undefined> {
    const suffix = lock ? Prisma.sql`FOR UPDATE` : Prisma.empty;
    const rows =
        workflow === "comedian_identity"
            ? await tx.$queryRaw<Row[]>(
                  Prisma.sql`SELECT ${candidateColumns} FROM comedian_identity_candidates WHERE uuid=${id} ${suffix}`,
              )
            : await tx.$queryRaw<Row[]>(
                  Prisma.sql`SELECT ${associationColumns} FROM comedian_podcasts WHERE id::text=${id} ${suffix}`,
              );
    return rows[0];
}
export async function searchReviewComedians(q: string, tx: Tx = db) {
    if (!q.trim()) return [];
    return tx.$queryRaw<
        { id: number; name: string }[]
    >`SELECT id,name FROM comedians c
 WHERE c.parent_comedian_id IS NULL AND c.visible AND (position(lower(${q.trim()}) in lower(c.name))>0 OR position(lower(c.name) in lower(${q.trim()}))>0)
 AND NOT EXISTS (SELECT 1 FROM comedian_deny_list d WHERE lower(btrim(regexp_replace(replace(d.name,chr(160),' '),'[[:space:]]+',' ','g')))=lower(btrim(regexp_replace(replace(c.name,chr(160),' '),'[[:space:]]+',' ','g'))))
 ORDER BY (lower(c.name)=lower(${q.trim()})) DESC,c.total_shows DESC,c.id LIMIT 12`;
}
export async function listReviews(
    input: z.input<typeof reviewFilters>,
): Promise<ReviewPage> {
    const parsed = reviewFilters.parse(input);
    const f = {
        ...parsed,
        status:
            parsed.status ?? reviewDefinitions[parsed.workflow].defaultStatus,
    };
    if (
        !reviewDefinitions[f.workflow].statuses.some(
            (s) => s.value === f.status,
        )
    )
        throw new ReviewConflict("Invalid status for this review type.");
    if (
        f.workflow === "comedian_visibility" ||
        f.workflow === "club_visibility"
    )
        return listVisibilityReviews(f.workflow, f.status, f.q, f.page);
    if (f.workflow === "event_eligibility")
        return listEventInbox(
            {
                q: f.q,
                status: eventReviewFilters.shape.status.parse(
                    f.status === "all" ? undefined : f.status,
                ),
                source: f.source,
                mode: f.mode,
                after: f.after,
                ceiling: f.ceiling,
            },
            f.page,
        );
    const offset = (f.page - 1) * 30;
    const rows =
        f.workflow === "comedian_identity"
            ? await db.$queryRaw<
                  Row[]
              >`SELECT uuid AS id,name AS title,status,created_at FROM comedian_identity_candidates
 WHERE status=${f.status} AND position(lower(${f.q}) in lower(name))>0 ORDER BY created_at,uuid LIMIT 30 OFFSET ${offset}`
            : await db.$queryRaw<
                  Row[]
              >`SELECT cp.id::text AS id,p.title || ' · ' || c.name AS title,cp.review_status AS status,cp.created_at
 FROM comedian_podcasts cp JOIN podcasts p ON p.id=cp.podcast_id JOIN comedians c ON c.id=cp.comedian_id
 WHERE cp.review_status=${f.status} AND position(lower(${f.q}) in lower(p.title || ' ' || c.name))>0
 ORDER BY cp.created_at,cp.id LIMIT 30 OFFSET ${offset}`;
    const counts =
        f.workflow === "comedian_identity"
            ? await db.$queryRaw<
                  { total: number }[]
              >`SELECT count(*)::int AS total FROM comedian_identity_candidates WHERE status=${f.status} AND position(lower(${f.q}) in lower(name))>0`
            : await db.$queryRaw<
                  { total: number }[]
              >`SELECT count(*)::int AS total FROM comedian_podcasts cp JOIN podcasts p ON p.id=cp.podcast_id JOIN comedians c ON c.id=cp.comedian_id WHERE cp.review_status=${f.status} AND position(lower(${f.q}) in lower(p.title || ' ' || c.name))>0`;
    // Queue rows are light; source context is fetched only for the selected item.
    return {
        page: f.page,
        total: counts[0].total,
        items: rows.map((r) => ({
            id: r.id,
            workflow: f.workflow,
            title: r.title,
            subtitle:
                f.workflow === "comedian_identity"
                    ? "Validate identity"
                    : "Validate relationship",
            status: r.status,
            token: "",
            evidence: [],
            matches: [],
            history: [],
        })),
    };
}
export async function getReview(
    workflow: ReviewWorkflow,
    id: string,
): Promise<ReviewItem | null> {
    if (workflow === "comedian_visibility" || workflow === "club_visibility")
        return getVisibilityReview(workflow, id);
    if (workflow === "event_eligibility") {
        if (!/^[1-9]\d*$/.test(id) || Number(id) > 2147483647)
            throw new ReviewConflict("Invalid event ID.");
        return getEventInbox(id);
    }
    const row = await current(db, workflow, id);
    if (!row) return null;
    const history = await db.$queryRaw<
        ReviewItem["history"]
    >`SELECT id,action,reason,actor,created_at AS "createdAt",(undone_at IS NOT NULL) AS undone FROM admin_review_decisions WHERE workflow=${workflow} AND item_id=${id} ORDER BY created_at DESC LIMIT 30`;
    if (workflow === "comedian_identity") {
        const evidence = await db.$queryRaw<
            Row[]
        >`SELECT e.fingerprint AS id,e.raw_name AS title,e.context,e.source_url AS url,e.source_key AS source,e.extraction_kind AS kind,e.show_id AS "showId",s.date,s.name AS "showTitle"
 FROM comedian_identity_evidence e LEFT JOIN shows s ON s.id=e.show_id WHERE e.candidate_uuid=${id}
 ORDER BY (s.date>=now()) DESC NULLS LAST,s.date,e.fingerprint LIMIT 100`;
        return plain({
            id,
            workflow,
            title: row.name,
            subtitle:
                "Approval validates this identity. Select only appearances supported by the source.",
            status: row.status,
            token: token(row),
            evidence: evidence.map((e) => ({
                ...e,
                title: e.showTitle || e.title,
            })),
            matches: await searchReviewComedians(row.name),
            history,
        }) as ReviewItem;
    }
    const details = await db.$queryRaw<
        Row[]
    >`SELECT p.title,p.website_url,c.name,cp.association_type,cp.source,cp.evidence FROM comedian_podcasts cp JOIN podcasts p ON p.id=cp.podcast_id JOIN comedians c ON c.id=cp.comedian_id WHERE cp.id::text=${id}`;
    const d = details[0];
    return plain({
        id,
        workflow,
        title: d.title,
        subtitle: `${d.name} · ${d.association_type}`,
        actions: [],
        notice: "This legacy source review is read-only. Host decisions are now shared across sources.",
        status: row.review_status,
        token: token(row),
        matches: [],
        evidence: [
            {
                id,
                title: `${d.name} as ${d.association_type}`,
                context: JSON.stringify(d.evidence, null, 2),
                url: d.website_url,
                source: d.source,
                kind: "Podcast relationship",
            },
        ],
        history,
    }) as ReviewItem;
}
async function canonical(tx: Tx, id: number) {
    const rows = await tx.$queryRaw<
        Row[]
    >`SELECT id,uuid,name,visible,parent_comedian_id,identity_validated_at,identity_validated_by FROM comedians WHERE id=${id} FOR UPDATE`;
    const c = rows[0];
    if (!c || !c.visible || c.parent_comedian_id !== null)
        throw new ReviewConflict("Choose an active canonical comedian.");
    const denied = await tx.$queryRaw<
        Row[]
    >`SELECT name FROM comedian_deny_list WHERE lower(btrim(regexp_replace(replace(name,chr(160),' '),'[[:space:]]+',' ','g')))=lower(btrim(regexp_replace(replace(${c.name},chr(160),' '),'[[:space:]]+',' ','g'))) LIMIT 1`;
    if (denied.length)
        throw new ReviewConflict(
            "This comedian is denied. Resolve the block in comedian management first.",
        );
    return c;
}
function comedianUuid(name: string) {
    return createHash("md5")
        .update(
            Array.from(name)
                .filter(
                    (c) =>
                        /[0-9A-Za-z]/.test(c) ||
                        c.toLowerCase() !== c.toUpperCase(),
                )
                .join("")
                .toLowerCase(),
        )
        .digest("hex");
}
export async function decideReview(
    input: z.input<typeof reviewSubmission>,
    actor: string,
): Promise<ReviewResult> {
    const x = reviewSubmission.parse(input);
    if (
        !reviewDefinitions[x.workflow].actions.some((a) => a.value === x.action)
    )
        throw new ReviewConflict("Invalid action for this review type.");
    if (
        x.workflow === "comedian_visibility" ||
        x.workflow === "club_visibility"
    )
        return decideVisibilityReview({ ...x, workflow: x.workflow }, actor);
    if (x.workflow === "event_eligibility") {
        if (
            !x.requestId ||
            !/^[1-9]\d*$/.test(x.id) ||
            Number(x.id) > 2147483647
        )
            throw new ReviewConflict(
                "A valid event and request ID are required.",
            );
        try {
            const result = await submitEventReview(
                {
                    id: x.requestId,
                    candidateId: Number(x.id),
                    token: x.token,
                    action: x.action as "approve" | "reject" | "defer",
                    reason: x.reason,
                },
                actor,
            );
            return {
                status: result.status,
                notice:
                    result.status === "pending"
                        ? "Review submitted. The worker validates requests about every 15 minutes; scheduling can take longer. Publication is checked on the next scrape."
                        : `Review request ${result.status}. Refresh the event to see its current state.`,
            } satisfies ReviewResult;
        } catch (error) {
            if (error instanceof EventReviewConflict)
                throw new ReviewConflict(error.message);
            if (
                error &&
                typeof error === "object" &&
                "code" in error &&
                (error.code === "P2002" ||
                    (error.code === "P2010" &&
                        "meta" in error &&
                        JSON.stringify(error.meta).includes("23505")))
            )
                throw new ReviewConflict(
                    "A review was submitted concurrently. Refresh the event.",
                );
            throw error;
        }
    }
    if (x.workflow === "podcast_association")
        throw new ReviewConflict(
            "Host relationships require a versioned relationship decision; this legacy review is read-only.",
        );
    return db.$transaction(async (tx) => {
        const before = await current(tx, x.workflow, x.id, true);
        if (
            !before ||
            token(before) !== x.token ||
            (before.status ?? before.review_status) !== "pending"
        )
            throw new ReviewConflict(
                "This item changed. Refresh it before deciding.",
            );
        const effects: Row = {};
        if (x.workflow === "comedian_identity") {
            let target: Row | undefined;
            if (x.action !== "reject") {
                if (x.action === "link") {
                    if (!x.targetId)
                        throw new ReviewConflict(
                            "Choose the existing comedian to link.",
                        );
                    target = await canonical(tx, x.targetId);
                    await tx.$queryRaw`SELECT curation_approve_comedian(${x.id},${before.name},${actor},${x.reason},${target.id}::integer)`;
                } else {
                    const name = (x.name ?? before.name)
                        .trim()
                        .replace(/\s+/g, " ");
                    const uuid = comedianUuid(name);
                    const denied = await tx.$queryRaw<
                        Row[]
                    >`SELECT name FROM comedian_deny_list WHERE lower(btrim(regexp_replace(replace(name,chr(160),' '),'[[:space:]]+',' ','g')))=lower(btrim(regexp_replace(replace(${name},chr(160),' '),'[[:space:]]+',' ','g'))) LIMIT 1`;
                    if (denied.length)
                        throw new ReviewConflict(
                            "This name is denied. Resolve the block first.",
                        );
                    await tx.$queryRaw`SELECT curation_approve_comedian(${x.id},${name},${actor},${x.reason})`;
                    await tx.$queryRaw`SELECT curation_observe_comedian(${uuid},${name},'{"writer":"review"}'::jsonb)`;
                    const created = await tx.$queryRaw<
                        Row[]
                    >`INSERT INTO comedians(name,uuid) VALUES(${name},${uuid}) ON CONFLICT(uuid) DO UPDATE SET visible=true,block_reason=NULL,block_added_by=NULL,block_added_at=NULL
 WHERE comedians.block_reason='Identity approval undone' AND comedians.identity_validated_at IS NULL
 AND comedians.parent_comedian_id IS NULL AND comedians.block_added_by=${actor}
 RETURNING id`;
                    if (!created.length)
                        throw new ReviewConflict(
                            "This identity already exists. Use Link existing to validate it.",
                        );
                    effects.created = true;
                    target = await canonical(tx, created[0].id);
                }
                effects.comedianBefore = plain(target);
                await tx.$queryRaw`UPDATE comedians SET identity_validated_at=now(),identity_validated_by=${actor} WHERE id=${target!.id} RETURNING id`;
                // Appearance approval is deliberately separate from the identity decision.
                const links = await tx.$queryRaw<
                    Row[]
                >`INSERT INTO lineup_items(show_id,comedian_id)
 SELECT DISTINCT e.show_id,${target!.uuid} FROM comedian_identity_evidence e JOIN shows s ON s.id=e.show_id
 WHERE e.candidate_uuid=${x.id} AND e.show_id=ANY(${x.showIds}::int[])
 ON CONFLICT(show_id,comedian_id) DO NOTHING RETURNING show_id`;
                effects.showIds = links.map((r) => r.show_id);
                effects.comedianAfter = plain(await canonical(tx, target!.id));
            }
            await tx.$queryRaw`UPDATE comedian_identity_candidates SET status=${x.action === "reject" ? "rejected" : "accepted"},canonical_comedian_id=${target?.id ?? null},version=version+1,reviewed_by=${actor},reviewed_at=now(),reason=${x.reason},updated_at=now() WHERE uuid=${x.id} RETURNING uuid`;
        }
        if (x.workflow === "comedian_identity") {
            const versions = await tx.$queryRaw<
                Row[]
            >`SELECT e.version FROM curation_entities e JOIN curation_identity_keys k ON k.entity_id=e.id WHERE k.namespace='comedian-uuid:v1' AND k.scope='global' AND k.value=${x.id}`;
            effects.curationVersion = versions[0]?.version;
        }
        const after = await current(tx, x.workflow, x.id);
        const decisionId = randomUUID();
        await tx.$queryRaw`INSERT INTO admin_review_decisions(id,workflow,item_id,actor,action,reason,before_json,after_json)
 VALUES(${decisionId},${x.workflow},${x.id},${actor},${x.action},${x.reason},${JSON.stringify(before)}::jsonb,${JSON.stringify({ row: after, effects })}::jsonb) RETURNING id`;
        return { decisionId };
    });
}
export async function undoReview(decisionId: string, actor: string) {
    return db.$transaction(async (tx) => {
        const decisions = await tx.$queryRaw<
            Row[]
        >`SELECT * FROM admin_review_decisions WHERE id=${decisionId} FOR UPDATE`;
        const d = decisions[0];
        if (!d || d.actor !== actor || d.undone_at)
            throw new ReviewConflict("This decision cannot be undone.");
        if (d.workflow === "podcast_association")
            throw new ReviewConflict(
                "Restore or sever the host relationship explicitly; legacy undo cannot overwrite a pair decision.",
            );
        const row = await current(tx, d.workflow, d.item_id, true);
        if (!row || token(row) !== token(d.after_json.row))
            throw new ReviewConflict(
                "This item has changed since your decision.",
            );
        const e = d.after_json.effects,
            b = d.before_json;
        if (d.workflow === "comedian_identity") {
            if (e.comedianAfter) {
                const c = await canonical(tx, e.comedianAfter.id);
                if (token(c) !== token(e.comedianAfter))
                    throw new ReviewConflict(
                        "The comedian changed after approval; use comedian management to resolve it.",
                    );
                const other = await tx.$queryRaw<
                    Row[]
                >`SELECT uuid FROM comedian_identity_candidates WHERE canonical_comedian_id=${c.id} AND status='accepted' AND uuid<>${d.item_id} LIMIT 1`;
                if (other.length)
                    throw new ReviewConflict(
                        "Another approved identity now uses this comedian.",
                    );
                if (e.created) {
                    const used = await tx.$queryRaw<
                        Row[]
                    >`SELECT show_id FROM lineup_items WHERE comedian_id=${c.uuid} AND NOT(show_id=ANY(${e.showIds}::int[])) LIMIT 1`;
                    if (used.length)
                        throw new ReviewConflict(
                            "New appearances were added after approval. Resolve this in comedian management.",
                        );
                }
                await tx.$queryRaw`SELECT curation_reopen_comedian(${d.item_id},${actor},'Undo identity approval',${e.curationVersion ?? null}::integer)`;
                await tx.$queryRaw`DELETE FROM lineup_items WHERE comedian_id=${c.uuid} AND show_id=ANY(${e.showIds}::int[]) RETURNING show_id`;
                await tx.$queryRaw`UPDATE comedians SET identity_validated_at=${e.comedianBefore.identity_validated_at}::timestamptz,identity_validated_by=${e.comedianBefore.identity_validated_by} WHERE id=${c.id} RETURNING id`;
                if (e.created)
                    await tx.$queryRaw`UPDATE comedians SET visible=false,block_reason='Identity approval undone',block_added_by=${actor},block_added_at=now() WHERE id=${c.id} RETURNING id`;
            }
            if (!e.comedianAfter)
                await tx.$queryRaw`SELECT curation_reopen_comedian(${d.item_id},${actor},'Undo identity rejection',${e.curationVersion ?? null}::integer)`;
            await tx.$queryRaw`UPDATE comedian_identity_candidates SET status='pending',canonical_comedian_id=NULL,reviewed_at=NULL,reviewed_by=NULL,reason=NULL,version=version+1,updated_at=now() WHERE uuid=${d.item_id} RETURNING uuid`;
        }
        await tx.$queryRaw`UPDATE admin_review_decisions SET undone_at=now() WHERE id=${decisionId} RETURNING id`;
        return { workflow: d.workflow, id: d.item_id };
    });
}
