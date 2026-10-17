import { Prisma } from "@prisma/client";
import { CurationError, type SqlClient, type Adapter } from "./decisions";
/** Expose only known policy failures, never raw database diagnostics. */
export async function validateParentEligibility(
    tx: SqlClient,
    relationshipId: string,
) {
    try {
        await tx.$queryRaw(
            Prisma.sql`SELECT curation_validate_parent(${relationshipId})`,
        );
    } catch (error) {
        const detail = error instanceof Error ? error.message : "";
        if (
            /Both performers require independent identity approval/.test(detail)
        ) {
            throw new CurationError(
                "endpoint_ineligible",
                "Both performers require independent identity approval. Choose a visible, approved canonical parent and resolve any name blocks first.",
            );
        }
        if (/Independent same-performer evidence is required/.test(detail)) {
            throw new CurationError(
                "evidence_required",
                "Independent same-performer evidence is required. An embedded name or event title cannot establish an alias.",
            );
        }
        throw error;
    }
}

export const parentAdapter: Adapter = {
    mode: "immediate",
    async validate(tx, target, _snapshot, command) {
        if (target.type !== "relationship" || target.kind !== "alias_of")
            throw new CurationError(
                "unsupported",
                "Choose a parent relationship.",
            );
        if (command.action === "confirm")
            await validateParentEligibility(tx, target.id);
    },
    async preview(tx, target, _snapshot, command) {
        const [row] = await tx.$queryRaw<{ child: string; parent: string }[]>(
            Prisma.sql`SELECT s.label child,t.label parent FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id WHERE r.id=${target.id}`,
        );
        return [
            `${row.child} → ${row.parent}: ${command.action}.`,
            "Update canonical resolution and public grouping. Preserve original lineup, appearance, host, favorite and attribution records; do not transfer or delete them.",
            "Neither performer is blocked, deleted or identity-approved. Restore reopens this pair for review only.",
        ];
    },
    async apply() {
        /* Ledger trigger projects the confirmed parent atomically. */
    },
};
