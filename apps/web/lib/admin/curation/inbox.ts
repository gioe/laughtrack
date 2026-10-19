import { Prisma } from "@prisma/client";
import { z } from "zod";
import type { SqlClient, Target } from "./decisions";
import { CurationError } from "./decisions";
import type { InboxSummary, InboxDetail } from "./inboxTypes";
export const inboxQuery = z.object({
    view: z.enum(["intake", "relationships"]).default("intake"),
    kind: z
        .enum([
            "all",
            "comedian",
            "club",
            "show",
            "podcast",
            "alias_of",
            "host_of",
            "cohost_of",
        ])
        .default("all"),
    state: z
        .enum([
            "all",
            "pending",
            "approved",
            "blocked",
            "proposed",
            "confirmed",
            "rejected",
            "severed",
        ])
        .default("all"),
    q: z.string().max(200).default(""),
    page: z.coerce.number().int().min(1).max(10000).default(1),
    id: z.string().max(200).optional(),
    recordId: z.coerce.number().int().positive().optional(),
    endpointKind: z.enum(["comedian", "podcast"]).optional(),
    lookup: z.enum(["comedian", "podcast"]).optional(),
});
type Query = z.infer<typeof inboxQuery>;
type Row = {
    id: string;
    kind: Target["kind"];
    identity_scope: "entity" | "name" | "series";
    label: string;
    disposition: string;
    version: number;
    record_id: number | null;
    source_label?: string;
    target_label?: string;
    source_record_id?: number;
    target_record_id?: number;
};
function summary(r: Row, relationship = false): InboxSummary {
    return {
        target: relationship
            ? {
                  type: "relationship",
                  id: r.id,
                  kind: r.kind as "alias_of" | "host_of" | "cohost_of",
              }
            : {
                  type: "entity",
                  id: r.id,
                  kind: r.kind as "comedian" | "club" | "show" | "podcast",
                  scope: r.identity_scope,
              },
        label: r.label,
        state: r.disposition,
        version: r.version,
        recordId: r.record_id,
        sourceLabel: r.source_label,
        targetLabel: r.target_label,
        sourceRecordId: r.source_record_id,
        targetRecordId: r.target_record_id,
    };
}
export function createInbox(store: SqlClient) {
    async function rows(q: Query) {
        const rel = q.view === "relationships";
        const select = rel
            ? Prisma.sql`SELECT r.id,r.kind,'entity' identity_scope,s.label||' → '||t.label label,r.disposition,r.version,NULL::integer record_id,s.label source_label,t.label target_label,s.comedian_id source_record_id,coalesce(t.comedian_id,t.podcast_id) target_record_id FROM curation_relationships r JOIN curation_entities s ON s.id=r.source_id JOIN curation_entities t ON t.id=r.target_id`
            : Prisma.sql`SELECT e.*,coalesce(e.comedian_id,e.club_id,e.show_id,e.podcast_id) record_id FROM curation_entities e`;
        const alias = Prisma.raw(rel ? "r" : "e");
        const search = rel
            ? Prisma.sql`s.label||' '||t.label`
            : Prisma.sql`e.label`;
        const record = q.recordId
            ? rel
                ? q.endpointKind === "podcast"
                    ? Prisma.sql`t.podcast_id=${q.recordId}`
                    : Prisma.sql`(s.comedian_id=${q.recordId} OR t.comedian_id=${q.recordId})`
                : Prisma.sql`coalesce(e.comedian_id,e.club_id,e.show_id,e.podcast_id)=${q.recordId}`
            : Prisma.sql`true`;
        const found = await store.$queryRaw<Row[]>(
            Prisma.sql`${select} WHERE ${q.id ? Prisma.sql`${alias}.id=${q.id}` : Prisma.sql`(${q.kind}='all' OR ${alias}.kind=${q.kind}) AND (${q.state}='all' OR ${alias}.disposition=${q.state}) AND position(lower(${q.q}) in lower(${search}))>0 AND ${record}`} ORDER BY ${alias}.created_at,${alias}.id LIMIT 31 OFFSET ${(q.page - 1) * 30}`,
        );
        return found.map((r) => summary(r, rel));
    }
    async function detail(item: InboxSummary): Promise<InboxDetail> {
        const rel = item.target.type === "relationship",
            col = Prisma.raw(rel ? "relationship_id" : "entity_id"),
            id = item.target.id;
        const [
            keys,
            observations,
            decisions,
            requests,
            matches,
            reconciliations,
            candidates,
        ] = await Promise.all([
            rel
                ? []
                : store.$queryRaw<InboxDetail["keys"]>(
                      Prisma.sql`SELECT namespace,scope,value,key_type FROM curation_identity_keys WHERE entity_id=${id} ORDER BY namespace,scope,value`,
                  ),
            store.$queryRaw<InboxDetail["observations"]>(
                Prisma.sql`SELECT id,source,source_key,evidence,recorded_at FROM curation_observations WHERE ${col}=${id} ORDER BY recorded_at DESC,id LIMIT 100`,
            ),
            store.$queryRaw<InboxDetail["decisions"]>(
                Prisma.sql`SELECT * FROM curation_decisions WHERE ${col}=${id} ORDER BY version DESC`,
            ),
            store.$queryRaw<InboxDetail["requests"]>(
                Prisma.sql`SELECT id,status,action,reason,actor,error FROM curation_requests WHERE ${col}=${id} ORDER BY created_at DESC LIMIT 30`,
            ),
            rel
                ? []
                : store.$queryRaw<Row[]>(
                      Prisma.sql`SELECT e.*,coalesce(e.comedian_id,e.club_id,e.show_id,e.podcast_id) record_id FROM curation_entities e WHERE e.kind=${item.target.kind} AND e.id<>${id} AND lower(e.label)=lower(${item.label}) ORDER BY e.id LIMIT 20`,
                  ),
            rel && item.target.kind !== "alias_of"
                ? store.$queryRaw<InboxDetail["reconciliations"]>(
                      Prisma.sql`SELECT id,resolved_at,actor,reason FROM curation_host_reconciliations WHERE old_relationship_id=${id} OR new_relationship_id=${id} ORDER BY created_at`,
                  )
                : [],
            !rel && item.target.kind === "comedian"
                ? store.$queryRaw<{ uuid: string }[]>(
                      Prisma.sql`SELECT c.uuid FROM comedian_identity_candidates c JOIN curation_identity_keys k ON k.value=c.uuid AND k.scope='global' WHERE k.entity_id=${id} AND (k.namespace='comedian-uuid:v1' OR k.namespace LIKE 'legacy:%:comedian_identity_candidates:v1') LIMIT 1`,
                  )
                : [],
        ]);
        return {
            ...item,
            keys,
            observations,
            decisions,
            requests,
            matches: matches.map((r) => summary(r)),
            reconciliations,
            candidateId: candidates[0]?.uuid ?? null,
        };
    }
    async function get(input: unknown) {
        const q = inboxQuery.parse(input);
        if (q.lookup) {
            const found = await store.$queryRaw<Row[]>(
                Prisma.sql`SELECT e.*,coalesce(e.comedian_id,e.podcast_id) record_id FROM curation_entities e WHERE e.kind=${q.lookup} AND e.identity_scope='entity' AND coalesce(e.comedian_id,e.podcast_id) IS NOT NULL AND position(lower(${q.q}) in lower(e.label))>0 ORDER BY e.label,e.id LIMIT 20`,
            );
            return { items: found.map((r) => summary(r)), hasMore: false };
        }
        const items = await rows(q);
        if (q.id) {
            if (!items[0])
                throw new CurationError(
                    "not_found",
                    "Review item not found.",
                    404,
                );
            return detail(items[0]);
        }
        return { items: items.slice(0, 30), hasMore: items.length > 30 };
    }
    return { get };
}
