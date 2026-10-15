import { Prisma } from "@prisma/client";
import { CurationError, type Adapter, type SqlClient } from "./decisions";
type Row = Record<string, any>;
async function venue(tx: SqlClient, id: string) {
    const [entity] = await tx.$queryRaw<Row[]>(
        Prisma.sql`SELECT * FROM curation_entities WHERE id=${id}`,
    );
    if (entity.club_id) {
        const [row] = await tx.$queryRaw<Row[]>(
            Prisma.sql`SELECT to_jsonb(c) AS venue FROM clubs c WHERE id=${entity.club_id}`,
        );
        return { entity, payload: row?.venue };
    }
    const [row] = await tx.$queryRaw<Row[]>(
        Prisma.sql`SELECT evidence->'venue' AS venue FROM curation_observations WHERE entity_id=${id} AND evidence ? 'venue' ORDER BY recorded_at DESC,id DESC LIMIT 1`,
    );
    return { entity, payload: row?.venue };
}
export const clubAdapter: Adapter = {
    mode: "immediate",
    async validate(tx, target, _snapshot, command) {
        if (
            target.type !== "entity" ||
            target.kind !== "club" ||
            target.scope !== "entity"
        )
            throw new CurationError("unsupported", "Choose a venue identity.");
        if (command.action !== "approve") return;
        const { payload } = await venue(tx, target.id);
        if (!payload?.name || !payload?.address)
            throw new CurationError(
                "evidence_required",
                "Review a venue name and address before approval.",
            );
        const [policy] = await tx.$queryRaw<Row[]>(
            Prisma.sql`SELECT * FROM curation_club_policy(${JSON.stringify(payload)}::jsonb)`,
        );
        if (
            policy?.disposition === "blocked" ||
            policy?.entity_id !== target.id
        )
            throw new CurationError(
                "identity_conflict",
                "Resolve the venue denial or ambiguous identity before approval.",
            );
    },
    async preview(_tx, _target, _snapshot, command) {
        if (command.action === "block")
            return [
                "Hide this club and its existing shows; prevent new admission and source reactivation.",
                "Keep operating status, source configuration and comedy policy unchanged.",
            ];
        if (command.action === "restore")
            return [
                "Return to pending review without republishing clubs or shows, enabling sources, or changing comedy policy.",
            ];
        return [
            "Approve the venue identity and create a public club only when one does not exist.",
            "Existing visibility, source enablement and comedy settings remain unchanged.",
        ];
    },
    async apply(tx, target, _snapshot, command) {
        if (target.type !== "entity" || command.action !== "approve") return; // Block projection is enforced by the ledger trigger; restore only changes disposition.
        const { entity, payload } = await venue(tx, target.id);
        if (entity.club_id) return;
        const created = await tx.$queryRaw<Row[]>(
            Prisma.sql`INSERT INTO clubs(name,address,website,city,state,country,google_place_id) VALUES(${payload.name},${payload.address},${payload.website ?? ""},${payload.city ?? null},${payload.state ?? null},${payload.country ?? null},${payload.google_place_id ?? null}) ON CONFLICT(name) DO NOTHING RETURNING id`,
        );
        if (created.length !== 1)
            throw new CurationError(
                "identity_conflict",
                "A club already uses this display name. Reconcile its location before publishing.",
            );
    },
};
