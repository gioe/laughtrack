import { Prisma } from "@prisma/client";
import { randomUUID } from "node:crypto";
import { ReviewConflict } from "./reviewErrors";
type Tx = Pick<Prisma.TransactionClient, "$queryRaw">;
type Row = Record<string, any>;

export async function resolveJointBilling(
    tx: Tx,
    input: {
        id: string;
        evidenceId?: string;
        targetIds: number[];
        showIds: number[];
        reason: string;
    },
    actor: string,
) {
    const ids = [...new Set(input.targetIds)].sort((a, b) => a - b);
    if (ids.length < 2 || ids.length !== input.targetIds.length)
        throw new ReviewConflict(
            "Choose at least two distinct, validated comedians.",
        );
    const evidence = await tx.$queryRaw<
        Row[]
    >`SELECT e.*,s.club_id FROM comedian_identity_evidence e JOIN shows s ON s.id=e.show_id WHERE fingerprint=${input.evidenceId ?? ""} AND candidate_uuid=${input.id} FOR SHARE OF e,s`;
    const e = evidence[0];
    if (
        !e ||
        !e.source_key.trim() ||
        e.source_key === "unknown" ||
        !e.raw_name.trim()
    )
        throw new ReviewConflict(
            "Choose recorded evidence with a known source for this billing.",
        );
    const blocked = await tx.$queryRaw<
        Row[]
    >`SELECT * FROM curation_comedian_policy(${input.id},${e.raw_name}) WHERE disposition='blocked'`;
    if (blocked.length)
        throw new ReviewConflict(
            "Restore this blocked billing before resolving it.",
        );
    const members = await tx.$queryRaw<
        Row[]
    >`SELECT c.id,c.uuid,c.name FROM comedians c
        CROSS JOIN LATERAL curation_comedian_policy(c.uuid,c.name,c.id) p
        WHERE c.id=ANY(${ids}::int[]) AND c.visible AND c.parent_comedian_id IS NULL
        AND c.identity_validated_at IS NOT NULL AND p.disposition='approved' AND p.comedian_id=c.id
        ORDER BY c.id FOR UPDATE OF c`;
    if (members.length !== ids.length)
        throw new ReviewConflict(
            "Every member must be an approved, validated canonical comedian. Review their identities first.",
        );
    const shows = await tx.$queryRaw<
        Row[]
    >`SELECT DISTINCT show_id FROM comedian_identity_evidence
        WHERE candidate_uuid=${input.id} AND source_key=${e.source_key} AND raw_name=${e.raw_name}
        AND show_id IN (SELECT id FROM shows WHERE club_id=${e.club_id})
        AND show_id=ANY(${input.showIds}::int[])`;
    if (shows.length !== new Set(input.showIds).size)
        throw new ReviewConflict(
            "Select only appearances evidenced by this exact billing and source.",
        );
    const previous = await tx.$queryRaw<
        Row[]
    >`SELECT id,active FROM billing_credits WHERE source_key=${e.source_key} AND club_id=${e.club_id} AND raw_name=${e.raw_name} AND active FOR UPDATE`;
    if (previous[0]?.active)
        throw new ReviewConflict(
            "This billing already has an active mapping. Refresh the review.",
        );
    const creditId = randomUUID();
    await tx.$queryRaw`INSERT INTO billing_credits(id,candidate_uuid,source_key,club_id,raw_name,reviewed_by,reason)
        VALUES(${creditId},${input.id},${e.source_key},${e.club_id},${e.raw_name},${actor},${input.reason}) RETURNING id`;
    for (const member of members)
        await tx.$queryRaw`INSERT INTO billing_credit_members(credit_id,comedian_id) VALUES(${creditId},${member.id}) RETURNING comedian_id`;
    const added: { showId: number; uuid: string }[] = [];
    for (const show of shows) {
        await tx.$queryRaw`INSERT INTO show_billing_credits(credit_id,show_id) VALUES(${creditId},${show.show_id}) ON CONFLICT DO NOTHING RETURNING show_id`;
        for (const member of members) {
            const links = await tx.$queryRaw<
                Row[]
            >`INSERT INTO lineup_items(show_id,comedian_id) VALUES(${show.show_id},${member.uuid}) ON CONFLICT DO NOTHING RETURNING show_id`;
            added.push(
                ...links.map((r) => ({ showId: r.show_id, uuid: member.uuid })),
            );
        }
    }
    await tx.$queryRaw`UPDATE comedian_identity_candidates SET status=CASE WHEN EXISTS(
        SELECT 1 FROM comedian_identity_evidence e LEFT JOIN shows s ON s.id=e.show_id
        WHERE e.candidate_uuid=${input.id} AND NOT EXISTS(
          SELECT 1 FROM billing_credits b WHERE b.active AND b.candidate_uuid=e.candidate_uuid
          AND b.source_key=e.source_key AND b.raw_name=e.raw_name AND b.club_id=s.club_id)
        ) THEN 'pending' ELSE 'resolved' END,canonical_comedian_id=NULL,version=version+1,reviewed_by=${actor},reviewed_at=now(),reason=${input.reason},updated_at=now() WHERE uuid=${input.id} RETURNING uuid`;
    return {
        creditId,
        members,
        added,
        showIds: shows.map((s) => s.show_id),
        source: e.source_key,
        rawName: e.raw_name,
    };
}

export async function undoJointBilling(
    tx: Tx,
    effect: {
        creditId: string;
        added: { showId: number; uuid: string }[];
        showIds: number[];
    },
) {
    const extra = await tx.$queryRaw<
        Row[]
    >`SELECT show_id FROM show_billing_credits WHERE credit_id=${effect.creditId} AND NOT(show_id=ANY(${effect.showIds}::int[])) LIMIT 1`;
    // Never silently undo appearances attached by a subsequent scrape.
    if (extra.length)
        throw new ReviewConflict(
            "This mapping has been used on more shows. Review those appearances before undoing it.",
        );
    await tx.$queryRaw`UPDATE billing_credits SET active=false WHERE id=${effect.creditId} RETURNING id`;
    for (const link of effect.added)
        await tx.$queryRaw`DELETE FROM lineup_items l WHERE show_id=${link.showId} AND comedian_id=${link.uuid}
        AND NOT EXISTS(SELECT 1 FROM show_billing_credits sb JOIN billing_credit_members m ON m.credit_id=sb.credit_id JOIN comedians c ON c.id=m.comedian_id JOIN billing_credits b ON b.id=sb.credit_id WHERE sb.show_id=l.show_id AND c.uuid=l.comedian_id AND b.active) RETURNING show_id`;
    await tx.$queryRaw`DELETE FROM show_billing_credits WHERE credit_id=${effect.creditId} RETURNING show_id`;
}
