import { createHash } from "node:crypto";
import { Prisma } from "@prisma/client";
import { z } from "zod";
import {
    CurationError,
    createCurationService,
    type SqlClient,
    type Store,
} from "./decisions";
import { parentAdapter, validateParentEligibility } from "./parentAdapter";
export const parentEvidenceSchema = z
    .object({
        samePerformer: z.literal(true),
        sourceUrl: z
            .string()
            .url()
            .regex(/^https?:/),
        explanation: z.string().trim().min(20).max(2000),
    })
    .strict();
export const parentChangeSchema = z
    .object({
        childId: z.number().int().positive(),
        parentId: z.number().int().positive().nullable(),
        reason: z.string().trim().min(1).max(2000),
        requestId: z.string().uuid(),
        previewToken: z.string().optional(),
    })
    .strict();
type Change = z.infer<typeof parentChangeSchema>;
type Row = Record<string, any>;
const hash = (value: unknown) =>
    createHash("sha256").update(JSON.stringify(value)).digest("hex");
const severRequest = (id: string) => {
    const h = hash([id, "sever"]);
    return `${h.slice(0, 8)}-${h.slice(8, 12)}-4${h.slice(13, 16)}-a${h.slice(17, 20)}-${h.slice(20, 32)}`;
};
async function plan(tx: SqlClient, x: Change) {
    const people = await tx.$queryRaw<Row[]>(
        Prisma.sql`SELECT c.id,c.name,c.parent_comedian_id,c.visible,c.identity_validated_at,e.id entity_id,e.version,e.disposition FROM comedians c LEFT JOIN curation_entities e ON e.comedian_id=c.id WHERE c.id=${x.childId} OR c.id=${x.parentId} ORDER BY c.id`,
    );
    const child = people.find((p) => p.id === x.childId),
        parent = people.find((p) => p.id === x.parentId);
    if (!child || (x.parentId !== null && !parent))
        throw new CurationError(
            "not_found",
            "Comedian endpoint not found.",
            404,
        );
    if (x.childId === x.parentId)
        throw new CurationError(
            "self_parent",
            "A comedian cannot be their own parent.",
            400,
        );
    const edges = await tx.$queryRaw<Row[]>(
        Prisma.sql`SELECT r.*,t.comedian_id parent_id,t.label parent_name,(SELECT jsonb_agg(o.evidence ORDER BY o.recorded_at,o.id) FROM curation_observations o WHERE o.relationship_id=r.id) evidence FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id WHERE r.kind='alias_of' AND s.comedian_id=${x.childId} ORDER BY r.id`,
    );
    const active = edges.find((e) => e.disposition === "confirmed");
    if ((active?.parent_id ?? null) !== child.parent_comedian_id)
        throw new CurationError(
            "projection_conflict",
            "Reconcile the legacy parent link before editing.",
        );
    const desired =
        x.parentId === null
            ? active
            : edges.find((e) => e.parent_id === x.parentId);
    if (!desired)
        throw new CurationError(
            "proposal_required",
            x.parentId === null
                ? "There is no confirmed parent to sever."
                : "Propose this pair with independent same-performer evidence first.",
        );
    if (x.parentId !== null && desired.disposition !== "proposed")
        throw new CurationError(
            "restore_required",
            "This pair is already decided. Explicitly restore a rejected or severed relationship before confirming it.",
        );
    if (x.parentId !== null) await validateParentEligibility(tx, desired.id);
    const effects = [
        ...(active && x.parentId !== null
            ? [
                  `Sever ${child.name} → ${active.parent_name}; retain this negative decision.`,
              ]
            : []),
        `${x.parentId === null ? "Sever" : "Confirm"} ${child.name} → ${desired.parent_name}.`,
        "Public canonical grouping changes. Preserve original lineup, appearance, attribution, host and favorite records; do not migrate or delete them.",
        "Neither comedian is blocked or identity-approved.",
    ];
    return {
        child,
        active,
        desired,
        effects,
        previewToken: hash({
            people,
            edges,
            childId: x.childId,
            parentId: x.parentId,
            reason: x.reason,
        }),
    };
}
export function createParentRelationshipService(
    store: Store,
    invalidate: () => Promise<void>,
) {
    async function propose(input: unknown, actor: string) {
        const x = z
            .object({
                childId: z.number().int().positive(),
                parentId: z.number().int().positive(),
                reason: z.string().trim().min(1).max(2000),
                evidence: parentEvidenceSchema,
            })
            .strict()
            .parse(input);
        return store.$transaction(async (tx) => {
            const [row] = await tx.$queryRaw<{ id: string }[]>(
                Prisma.sql`SELECT curation_propose_parent(${x.childId},${x.parentId},${JSON.stringify(x.evidence)}::jsonb,${actor},${x.reason}) id`,
            );
            return { relationshipId: row.id };
        });
    }
    async function preview(input: unknown) {
        const x = parentChangeSchema.parse(input);
        return store.$transaction(async (tx) => {
            const p = await plan(tx, x);
            return {
                previewToken: p.previewToken,
                effects: p.effects,
                relationshipId: p.desired.id,
                version: p.desired.version,
            };
        });
    }
    async function submit(input: unknown, actor: string) {
        const x = parentChangeSchema.parse(input);
        if (!x.previewToken)
            throw new CurationError(
                "preview_required",
                "Preview the relationship change first.",
                400,
            );
        const result = await store.$transaction(async (tx) => {
            await tx.$queryRaw(Prisma.sql`SELECT curation_lock_intake()`);
            const [receipt] = await tx.$queryRaw<Row[]>(
                Prisma.sql`SELECT q.*,s.comedian_id child,t.comedian_id parent FROM curation_requests q JOIN curation_relationships r ON r.id=q.relationship_id JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id WHERE q.id=${x.requestId}`,
            );
            if (receipt) {
                if (
                    receipt.child !== x.childId ||
                    (x.parentId !== null && receipt.parent !== x.parentId) ||
                    receipt.action !==
                        (x.parentId === null ? "sever" : "confirm") ||
                    receipt.reason !== x.reason ||
                    receipt.actor !== actor
                )
                    throw new CurationError(
                        "idempotency_conflict",
                        "Request ID belongs to another change.",
                    );
                if (receipt.status === "applied") return receipt;
            }
            const p = await plan(tx, x);
            if (p.previewToken !== x.previewToken)
                throw new CurationError(
                    "stale_preview",
                    "The relationship or an endpoint changed. Preview again.",
                );
            const service = createCurationService({
                store: {
                    $queryRaw: (q) => tx.$queryRaw(q),
                    $transaction: (fn) => fn(tx),
                },
                adapter: () => parentAdapter,
                invalidate: async () => {},
            });
            async function decide(
                edge: Row,
                action: "sever" | "confirm",
                requestId: string,
            ) {
                const result = await service.submit(
                    {
                        requestId,
                        target: {
                            type: "relationship",
                            kind: "alias_of",
                            id: edge.id,
                        },
                        expectedVersion: edge.version,
                        action,
                        reason: x.reason,
                    },
                    actor,
                );
                if (result.status !== "applied")
                    throw new CurationError(
                        "relationship_conflict",
                        result.error ?? "Relationship change failed.",
                    );
                return result;
            }
            if (p.active && x.parentId !== null)
                await decide(p.active, "sever", severRequest(x.requestId));
            return decide(
                p.desired,
                x.parentId === null ? "sever" : "confirm",
                x.requestId,
            );
        });
        await invalidate();
        return result;
    }
    async function history(childId: number) {
        return store.$queryRaw<Row[]>(
            Prisma.sql`SELECT r.*,s.comedian_id child_id,s.label child_name,t.comedian_id parent_id,t.label parent_name,coalesce((SELECT jsonb_agg(to_jsonb(d) ORDER BY d.version) FROM curation_decisions d WHERE d.relationship_id=r.id),'[]'::jsonb) decisions,coalesce((SELECT jsonb_agg(to_jsonb(o) ORDER BY o.recorded_at) FROM curation_observations o WHERE o.relationship_id=r.id),'[]'::jsonb) observations FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id WHERE r.kind='alias_of' AND s.comedian_id=${childId} ORDER BY r.created_at,r.id`,
        );
    }
    return { propose, preview, submit, history };
}
