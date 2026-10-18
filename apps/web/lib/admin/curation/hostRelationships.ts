import { Prisma } from "@prisma/client";
import { createHash } from "node:crypto";
import { z } from "zod";
import {
    CurationError,
    createCurationService,
    type SqlClient,
    type Store,
} from "./decisions";
import { hostAdapter } from "./hostAdapter";
const proposal = z
    .object({
        comedianId: z.number().int().positive(),
        podcastId: z.number().int().positive(),
        role: z.enum(["host", "cohost"]),
        source: z.string().trim().min(1).max(200),
        sourceKey: z.string().trim().min(1).max(200),
        evidence: z.record(z.unknown()),
        reason: z.string().trim().min(1).max(2000),
    })
    .strict();
const hash = (value: unknown) =>
    createHash("sha256").update(JSON.stringify(value)).digest("hex");
async function reconciliation(tx: SqlClient, id: string) {
    const [row] = await tx.$queryRaw<Record<string, any>[]>(
        Prisma.sql`SELECT h.*,a.disposition old_state,a.version old_version,b.disposition new_state,b.version new_version,s.label old_comedian,n.label new_comedian,t.label podcast FROM curation_host_reconciliations h JOIN curation_relationships a ON a.id=h.old_relationship_id JOIN curation_relationships b ON b.id=h.new_relationship_id JOIN curation_entities s ON s.id=a.source_id JOIN curation_entities n ON n.id=b.source_id JOIN curation_entities t ON t.id=b.target_id WHERE h.id=${id}`,
    );
    if (!row)
        throw new CurationError(
            "not_found",
            "Identity reconciliation not found.",
            404,
        );
    return row;
}
export function createHostRelationshipService(
    store: Store,
    invalidate: () => Promise<void>,
) {
    const decisions = createCurationService({
        store,
        adapter: () => hostAdapter,
        invalidate,
    });
    async function propose(input: unknown, actor: string) {
        const x = proposal.parse(input);
        return store.$transaction(async (tx) => {
            const [row] = await tx.$queryRaw<{ id: string }[]>(
                Prisma.sql`SELECT curation_observe_host(${x.comedianId},${x.podcastId},${x.role},${x.source},${x.sourceKey},${JSON.stringify({ ...x.evidence, actor, reason: x.reason })}::jsonb) id`,
            );
            return { relationshipId: row.id };
        });
    }
    async function history(podcastId: number) {
        return store.$queryRaw<Record<string, any>[]>(
            Prisma.sql`SELECT r.*,s.comedian_id,s.label comedian,t.label podcast,coalesce((SELECT jsonb_agg(to_jsonb(o) ORDER BY o.recorded_at,o.id) FROM curation_observations o WHERE o.relationship_id=r.id),'[]'::jsonb) observations,coalesce((SELECT jsonb_agg(to_jsonb(d) ORDER BY d.version) FROM curation_decisions d WHERE d.relationship_id=r.id),'[]'::jsonb) decisions,coalesce((SELECT jsonb_agg(to_jsonb(h) ORDER BY h.created_at,h.id) FROM curation_host_reconciliations h WHERE h.old_relationship_id=r.id OR h.new_relationship_id=r.id),'[]'::jsonb) reconciliations FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id WHERE t.podcast_id=${podcastId} AND r.kind IN ('host_of','cohost_of') ORDER BY r.id`,
        );
    }
    async function previewReconciliation(id: string) {
        return store.$transaction(async (tx) => {
            const row = await reconciliation(tx, id);
            return {
                token: hash(row),
                effects: [
                    `Review identity change: ${row.old_comedian} → ${row.new_comedian} for ${row.podcast} (${row.role}).`,
                    `Retain old decision: ${row.old_state}; retain new decision: ${row.new_state}.`,
                    `Release this reconciliation hold only. No decisions are merged or overwritten; any rejected/severed pair still requires explicit restoration before confirmation.`,
                ],
                states: row,
            };
        });
    }
    async function reconcile(input: unknown, actor: string) {
        const x = z
            .object({
                id: z.string().min(1),
                requestId: z.string().uuid(),
                token: z.string().min(1),
                reason: z.string().trim().min(1).max(2000),
            })
            .strict()
            .parse(input);
        const result = await store.$transaction(async (tx) => {
            await tx.$queryRaw(Prisma.sql`SELECT curation_lock_intake()`);
            const row = await reconciliation(tx, x.id);
            if (row.resolved_at) {
                if (
                    row.request_id === x.requestId &&
                    row.actor === actor &&
                    row.reason === x.reason &&
                    row.preview_token === x.token
                )
                    return { status: "applied" };
                throw new CurationError(
                    "already_resolved",
                    "This identity change was already reviewed with another command.",
                );
            }
            if (hash(row) !== x.token)
                throw new CurationError(
                    "stale_reconciliation",
                    "A relationship changed. Preview the identity reconciliation again.",
                );
            await tx.$queryRaw(
                Prisma.sql`UPDATE curation_host_reconciliations SET resolved_at=now(),actor=${actor},reason=${x.reason},request_id=${x.requestId},preview_token=${x.token},reviewed_states=${JSON.stringify({ oldVersion: row.old_version, oldState: row.old_state, newVersion: row.new_version, newState: row.new_state })}::jsonb WHERE id=${x.id} RETURNING id`,
            );
            await tx.$queryRaw(
                Prisma.sql`SELECT curation_project_host(${row.old_relationship_id})`,
            );
            await tx.$queryRaw(
                Prisma.sql`SELECT curation_project_host(${row.new_relationship_id})`,
            );
            return { status: "applied" };
        });
        await invalidate();
        return result;
    }
    return {
        propose,
        history,
        preview: decisions.preview,
        submit: decisions.submit,
        previewReconciliation,
        reconcile,
    };
}
