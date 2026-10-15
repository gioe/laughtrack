import { Prisma } from "@prisma/client";
import { CurationError, type Adapter } from "./decisions";

export const showAdapter: Adapter = {
    mode: "immediate",
    async validate(tx, target) {
        if (
            target.type !== "entity" ||
            target.kind !== "show" ||
            target.scope === "name"
        )
            throw new CurationError(
                "unsupported",
                "Choose an occurrence or an identified series.",
            );
        if (target.scope === "series") {
            const keys = await tx.$queryRaw<
                { scope: string; value: string }[]
            >(Prisma.sql`
                SELECT k.scope,k.value FROM curation_identity_keys k JOIN scraping_sources s ON s.id::text=k.scope
                WHERE k.entity_id=${target.id} AND k.key_type='series_id' AND k.namespace='show-series:v1'`);
            if (keys.length !== 1)
                throw new CurationError(
                    "ambiguous_series",
                    "An explicit source-owned series ID is required; titles cannot define a series block.",
                );
        }
    },
    async preview(tx, target, _snapshot, command) {
        const keys = await tx.$queryRaw<
            { namespace: string; scope: string; value: string }[]
        >(Prisma.sql`
            SELECT namespace,scope,value FROM curation_identity_keys WHERE entity_id=${target.id} ORDER BY namespace,scope,value`);
        const shows = await tx.$queryRaw<
            { id: number; name: string; date: Date }[]
        >(Prisma.sql`
            SELECT s.id,s.name,s.date FROM shows s JOIN curation_show_affected(${target.id}) a ON a.id=s.id ORDER BY s.date,s.id`);
        const staged = await tx.$queryRaw<
            { id: string; label: string }[]
        >(Prisma.sql`
            WITH seeds AS (SELECT ${target.id}::text AS id UNION SELECT occurrence_id FROM curation_show_series_members WHERE series_id=${target.id}),
            members AS (SELECT DISTINCT g.id FROM seeds CROSS JOIN LATERAL curation_show_group(seeds.id) g)
            SELECT e.id,e.label FROM curation_entities e JOIN members m ON m.id=e.id
            WHERE e.kind='show' AND e.identity_scope='entity' AND e.show_id IS NULL ORDER BY e.id`);
        return [
            target.type === "entity" && target.scope === "series"
                ? "Explicit series: only occurrences mapped to this source-owned series, including future observations."
                : "One occurrence and its confirmed cross-source mappings; no same-title or series-wide ban.",
            `Identity scope: ${JSON.stringify(keys)}`,
            `Known affected events (${shows.length}): ${JSON.stringify(shows)}`,
            `Additional staged occurrence identities (${staged.length}): ${JSON.stringify(staged)}`,
            command.action === "block"
                ? "Suppress discovery, public detail and future promotions; retain saved-show, ticket and audit references."
                : "This changes only the selected curation hold. It does not republish shows or remove cancellation, club, eligibility or other occurrence/series holds.",
        ];
    },
    async apply() {
        // The ledger trigger projects blocks in the same transaction. Restore
        // reopens review without setting visibility; approval also preserves it.
    },
};
