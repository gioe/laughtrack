import { Prisma } from "@prisma/client";
import { CurationError, type Adapter } from "./decisions";

/** Identity approval still uses the performer review's evidence/name/appearance UI.
 * Shared decisions handle durable blocking and restoration, independently of visibility.
 */
export const comedianAdapter: Adapter = {
    mode: "immediate",
    async validate(_tx, target, _snapshot, command) {
        if (target.type !== "entity" || target.kind !== "comedian")
            throw new CurationError("unsupported", "Not a comedian identity");
        if (command.action === "approve")
            throw new CurationError(
                "review_required",
                "Use comedian identity review to validate performer evidence and choose appearances.",
            );
    },
    async preview(_tx, _target, _snapshot, command) {
        return command.action === "block"
            ? [
                  "Prevent canonical creation, enrichment and new lineup admission for this identity and its known aliases.",
                  "Keep existing profiles, appearances and decision history.",
              ]
            : [
                  "Reopen identity review without approving or publishing.",
                  "Other identity/name blocks and legacy hidden-name suppression remain effective.",
              ];
    },
    async apply(tx, target, _snapshot, command) {
        if (target.type !== "entity") return;
        await tx.$queryRaw(Prisma.sql`UPDATE comedian_identity_candidates c
   SET status=${command.action === "block" ? "rejected" : "pending"},version=c.version+1,updated_at=now(),
   reviewed_by=CASE WHEN ${command.action}='restore' THEN NULL ELSE d.actor END,
   reviewed_at=CASE WHEN ${command.action}='restore' THEN NULL ELSE d.created_at END,
   reason=CASE WHEN ${command.action}='restore' THEN NULL ELSE d.reason END
   FROM curation_identity_keys k JOIN curation_entities e ON e.id=k.entity_id JOIN curation_decisions d ON d.entity_id=e.id AND d.version=e.version WHERE k.entity_id=${target.id} AND (k.namespace='comedian-uuid:v1' OR k.namespace LIKE 'legacy:%:comedian_identity_candidates:v1') AND k.scope='global' AND k.value=c.uuid
   RETURNING c.uuid`);
    },
};
