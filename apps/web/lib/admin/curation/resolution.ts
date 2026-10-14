import { Prisma } from "@prisma/client";
import { validateIdentityKey, type IdentityKey } from "./contracts";
import type { SqlClient } from "./decisions";
/** Read-only resolution. Observations never override a durable negative decision. */
export async function resolveEntity(tx: SqlClient, keys: IdentityKey[]) {
    if (!keys.length)
        return { status: "review" as const, entityIds: [] as string[] };
    if (keys.some((key) => key.entityKind !== keys[0].entityKind))
        throw new Error("Resolve one entity kind at a time.");
    const clauses = keys.map((key) => {
        validateIdentityKey(key);
        return Prisma.sql`(k.entity_kind=${key.entityKind} AND k.namespace=${key.namespace} AND k.scope=${key.scope} AND k.value=${key.value} AND k.identity_scope=${key.identityScope} AND k.key_type=${key.keyType})`;
    });
    const rows = await tx.$queryRaw<
        { id: string; identity_scope: string; disposition: string }[]
    >(
        Prisma.sql`SELECT DISTINCT e.id,e.identity_scope,e.disposition FROM curation_identity_keys k JOIN curation_entities e ON e.id=k.entity_id WHERE ${Prisma.join(clauses, " OR ")}`,
    );
    const blocked = rows.filter((r) => r.disposition === "blocked");
    if (blocked.length)
        return {
            status: "blocked" as const,
            entityIds: blocked.map((r) => r.id),
        };
    const entities = rows.filter((r) => r.identity_scope === "entity");
    return {
        status:
            entities.length === 1 && entities[0].disposition === "approved"
                ? ("approved" as const)
                : ("review" as const),
        entityIds: entities.map((r) => r.id),
    };
}
export async function resolveRelationship(
    tx: SqlClient,
    kind: "alias_of" | "host_of" | "cohost_of",
    sourceId: string,
    targetId: string,
) {
    // One statement gives edge and endpoint dispositions from the same snapshot.
    const [row] = await tx.$queryRaw<
        {
            id: string | null;
            disposition: string | null;
            source_disposition: string;
            target_disposition: string;
        }[]
    >(Prisma.sql`
        SELECT r.id,r.disposition,s.disposition AS source_disposition,t.disposition AS target_disposition
        FROM curation_entities s JOIN curation_entities t ON t.id=${targetId}
        LEFT JOIN curation_relationships r ON r.source_id=s.id AND r.target_id=t.id AND r.kind=${kind}
        WHERE s.id=${sourceId} AND s.identity_scope='entity' AND t.identity_scope='entity'`);
    if (
        row &&
        (["rejected", "severed"].includes(row.disposition ?? "") ||
            row.source_disposition === "blocked" ||
            row.target_disposition === "blocked")
    )
        return { status: "blocked" as const, relationshipId: row.id };
    return {
        status:
            row?.disposition === "confirmed" &&
            row.source_disposition === "approved" &&
            row.target_disposition === "approved"
                ? ("confirmed" as const)
                : ("review" as const),
        relationshipId: row?.id ?? null,
    };
}
