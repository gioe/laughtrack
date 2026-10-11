import { createHash } from "node:crypto";
import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import { z } from "zod";

export const eventReviewFilters = z
    .object({
        q: z.string().trim().max(200).default(""),
        source: z.coerce.number().int().positive().max(2147483647).optional(),
        mode: z.enum(["off", "shadow", "enforce"]).optional(),
        status: z
            .enum([
                "review",
                "accept",
                "reject",
                "approve",
                "defer",
                "stale_review",
                "stale_policy",
                "awaiting_observation",
            ])
            .optional(),
        after: z.coerce.number().int().nonnegative().max(2147483647).default(0),
        ceiling: z.coerce
            .number()
            .int()
            .nonnegative()
            .max(2147483647)
            .optional(),
    })
    .strict();
export const eventReviewSubmission = z
    .object({
        id: z.string().uuid(),
        candidateId: z.number().int().positive().max(2147483647),
        token: z.string().regex(/^[a-f0-9]{64}$/),
        action: z.enum(["approve", "reject", "defer"]),
        reason: z.string().trim().min(1).max(2000),
    })
    .strict();
export type ReviewSubmission = z.infer<typeof eventReviewSubmission>;
export type ReviewScope = {
    candidate_id: number;
    source_id: number;
    observation_generation: string;
    review_version: number;
    decision_id: number | null;
    payload_fingerprint: string | null;
    identity_fingerprint: string | null;
    policy_version: number | null;
    gate_mode: string;
};
export type EventReviewRow = ReviewScope & {
    club_id: number;
    club_name: string;
    event_key: string;
    scraper_key: string;
    enabled: boolean;
    current_policy_version: number;
    source_policy: string;
    status: string;
    decision: string | null;
    classifier_version: string | null;
    payload: Record<string, unknown> | null;
    evidence: Record<string, unknown> | null;
    token: string;
    request_status: string | null;
};
export type ReviewRequest = {
    id: string;
    candidate_id: number;
    actor: string;
    action: string;
    reason: string;
    snapshot: ReviewScope;
    status: string;
    error: string | null;
    created_at: string;
};
export type EventReviewDetail = {
    current: EventReviewRow;
    history: Record<string, unknown>[];
    observations: Record<string, unknown>[];
    publications: Record<string, unknown>[];
    requests: ReviewRequest[];
};
export type EventReviewPage = {
    items: EventReviewRow[];
    ceiling: number;
    next: number | null;
};
export class EventReviewConflict extends Error {}

// Keep the token shape identical to ReviewStore._token. BigInt generations travel
// as decimal strings, preserving precision through browser JSON and the worker.
export function reviewScope(row: ReviewScope): ReviewScope {
    return {
        candidate_id: row.candidate_id,
        source_id: row.source_id,
        observation_generation: String(row.observation_generation),
        review_version: row.review_version,
        decision_id: row.decision_id,
        payload_fingerprint: row.payload_fingerprint,
        identity_fingerprint: row.identity_fingerprint,
        policy_version: row.policy_version,
        gate_mode: row.gate_mode,
    };
}
export function scopeToken(row: ReviewScope) {
    return createHash("sha256")
        .update(JSON.stringify(reviewScope(row)))
        .digest("hex");
}
function serialize<T>(value: T): T {
    return JSON.parse(
        JSON.stringify(value, (_key, item) =>
            typeof item === "bigint" ? item.toString() : item,
        ),
    );
}
function decorate(row: EventReviewRow): EventReviewRow {
    return serialize({
        ...row,
        observation_generation: String(row.observation_generation),
        token: scopeToken(row),
    });
}
const columns = Prisma.sql`
 c.id AS candidate_id,c.source_id,c.club_id,c.event_key,c.observation_generation::text,c.review_version,
 o.decision_id,o.baseline_identity_fingerprint AS identity_fingerprint,
 d.payload_fingerprint,d.policy_version,d.payload,d.evidence,d.decision,d.classifier_version,
 ss.comedy_policy_version AS current_policy_version,ss.comedy_gate_mode AS gate_mode,ss.enabled,
 ss.comedy_policy AS source_policy,cl.name AS club_name,ss.scraper_key,
 (SELECT status FROM comedy_admin_review_requests ar WHERE ar.candidate_id=c.id ORDER BY ar.created_at DESC,ar.id DESC LIMIT 1) AS request_status,
 CASE WHEN o.decision_id IS NULL THEN 'awaiting_observation'
 WHEN d.policy_version<>ss.comedy_policy_version THEN 'stale_policy'
 WHEN c.review_version>0 AND (o.baseline_identity_fingerprint,d.payload_fingerprint,d.policy_version)
 IS DISTINCT FROM (r.identity_fingerprint,r.payload_fingerprint,r.policy_version) THEN 'stale_review'
 WHEN c.review_version>0 THEN r.action ELSE d.decision END AS status`;
const joins = Prisma.sql`
 FROM comedy_event_candidates c JOIN clubs cl ON cl.id=c.club_id
 JOIN scraping_sources ss ON ss.id=c.source_id
 LEFT JOIN comedy_event_observations o ON o.candidate_id=c.id AND o.generation=c.observation_generation
 LEFT JOIN comedy_event_decisions d ON d.candidate_id=c.id AND d.id=o.decision_id
 LEFT JOIN comedy_event_reviews r ON r.candidate_id=c.id AND r.review_version=c.review_version`;

export async function listEventReviews(
    input: z.input<typeof eventReviewFilters>,
): Promise<EventReviewPage> {
    const filters = eventReviewFilters.parse(input);
    const ceiling =
        filters.ceiling ??
        (
            await db.$queryRaw<
                { id: number }[]
            >`SELECT coalesce(max(id),0)::integer AS id FROM comedy_event_candidates`
        )[0].id;
    const rows = await db.$queryRaw<EventReviewRow[]>(Prisma.sql`
 WITH current_rows AS (SELECT ${columns} ${joins} WHERE c.id>${filters.after} AND c.id<=${ceiling})
 SELECT * FROM current_rows WHERE
 (${filters.q}='' OR position(lower(${filters.q}) in lower(coalesce(payload->>'name','') || ' ' || club_name))>0)
 AND (${filters.source ?? null}::integer IS NULL OR source_id=${filters.source ?? null})
 AND (${filters.mode ?? null}::text IS NULL OR gate_mode=${filters.mode ?? null})
 AND (${filters.status ?? null}::text IS NULL OR status=${filters.status ?? null})
 ORDER BY candidate_id LIMIT 51`);
    return {
        items: rows.slice(0, 50).map(decorate),
        ceiling,
        next: rows.length > 50 ? rows[49].candidate_id : null,
    };
}
export async function getEventReview(
    candidateId: number,
): Promise<EventReviewDetail | null> {
    const rows = await db.$queryRaw<EventReviewRow[]>(
        Prisma.sql`SELECT ${columns} ${joins} WHERE c.id=${candidateId}`,
    );
    if (!rows[0]) return null;
    const [history, observations, publications, requests] = await Promise.all([
        db.$queryRaw<
            Record<string, unknown>[]
        >`SELECT * FROM comedy_event_reviews WHERE candidate_id=${candidateId} ORDER BY review_version DESC LIMIT 100`,
        db.$queryRaw<
            Record<string, unknown>[]
        >`SELECT o.generation::text,o.observed_at,d.decision,d.classifier_version FROM comedy_event_observations o JOIN comedy_event_decisions d ON d.id=o.decision_id WHERE o.candidate_id=${candidateId} ORDER BY o.generation DESC LIMIT 100`,
        db.$queryRaw<
            Record<string, unknown>[]
        >`SELECT show_id,published_at FROM comedy_event_publications WHERE candidate_id=${candidateId} ORDER BY published_at DESC LIMIT 100`,
        db.$queryRaw<
            ReviewRequest[]
        >`SELECT * FROM comedy_admin_review_requests WHERE candidate_id=${candidateId} ORDER BY created_at DESC,id DESC LIMIT 100`,
    ]);
    return serialize({
        current: decorate(rows[0]),
        history,
        observations,
        publications,
        requests,
    });
}
export async function submitEventReview(
    input: ReviewSubmission,
    actor: string,
): Promise<ReviewRequest> {
    const data = eventReviewSubmission.parse(input);
    return db.$transaction(async (tx) => {
        // Existing request IDs are immutable and exact retries return their result.
        const previous = await tx.$queryRaw<
            ReviewRequest[]
        >`SELECT * FROM comedy_admin_review_requests WHERE id=${data.id}`;
        if (previous[0]) {
            const r = previous[0];
            if (
                r.actor !== actor ||
                r.candidate_id !== data.candidateId ||
                r.action !== data.action ||
                r.reason !== data.reason ||
                scopeToken(r.snapshot) !== data.token
            )
                throw new EventReviewConflict(
                    "This request ID was already used for a different decision.",
                );
            return serialize(r);
        }
        const rows = await tx.$queryRaw<EventReviewRow[]>(
            Prisma.sql`SELECT ${columns} ${joins} WHERE c.id=${data.candidateId} FOR UPDATE OF c`,
        );
        const row = rows[0];
        if (
            !row ||
            scopeToken(row) !== data.token ||
            !row.enabled ||
            row.gate_mode === "off" ||
            !row.decision_id ||
            row.policy_version !== row.current_policy_version
        )
            throw new EventReviewConflict(
                "Evidence or source settings changed. Refresh and review the event again.",
            );
        // Candidate lock serializes submissions; worker independently checks live
        // identity and source state before applying. This is only a pending command.
        const pending = await tx.$queryRaw<
            { id: string }[]
        >`SELECT id FROM comedy_admin_review_requests WHERE candidate_id=${data.candidateId} AND status='pending'`;
        if (pending.length)
            throw new EventReviewConflict(
                "This event already has a pending review.",
            );
        const result = await tx.$queryRaw<
            ReviewRequest[]
        >`INSERT INTO comedy_admin_review_requests(id,candidate_id,actor,action,reason,snapshot)
            VALUES(${data.id},${data.candidateId},${actor},${data.action},${data.reason},${JSON.stringify(reviewScope(row))}::jsonb) RETURNING *`;
        return serialize(result[0]);
    });
}
