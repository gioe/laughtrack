import { randomUUID } from "node:crypto";
import { Prisma } from "@prisma/client";
import { z } from "zod";
import { normalizeExactNameV1 } from "./contracts";
import type { SqlClient, Store } from "./decisions";
import { lockMigration, MIGRATION } from "./migration";
type Row = Record<string, any>;
const field = (relationship: boolean) =>
    Prisma.raw(relationship ? "relationship_id" : "entity_id");
const table = (relationship: boolean) =>
    Prisma.raw(relationship ? "curation_relationships" : "curation_entities");
/** Compatibility overlay: either legacy or durable negative state suppresses. Never grants approval. */
export async function migrationCompatibility(
    tx: SqlClient,
    id: string,
    relationship = false,
): Promise<{
    blocked: boolean;
    legacyBlocked: boolean;
    reasons: string[];
    current: Row;
}> {
    const [current] = await tx.$queryRaw<Row[]>(
        Prisma.sql`SELECT * FROM ${table(relationship)} WHERE id=${id}`,
    );
    if (!current) throw new Error("Curation target not found.");
    const reasons: string[] = [];
    if (relationship) {
        const [source] = await tx.$queryRaw<Row[]>(
            Prisma.sql`SELECT * FROM curation_entities WHERE id=${current.source_id}`,
        );
        const [target] = await tx.$queryRaw<Row[]>(
            Prisma.sql`SELECT * FROM curation_entities WHERE id=${current.target_id}`,
        );
        if (current.kind !== "alias_of") {
            const role = current.kind === "host_of" ? "host" : "cohost";
            const keys = await tx.$queryRaw<Row[]>(
                Prisma.sql`SELECT * FROM curation_identity_keys WHERE entity_id=${current.target_id}`,
            );
            const candidates = keys
                .filter((k) => k.namespace.startsWith("provider:"))
                .map(
                    (k) =>
                        Prisma.sql`(source=${k.scope} AND source_podcast_id=${k.value})`,
                );
            const [counts] = await tx.$queryRaw<
                { count: number }[]
            >(Prisma.sql`SELECT (
    (SELECT count(*) FROM comedian_podcasts WHERE comedian_id=${source.comedian_id} AND podcast_id=${target.podcast_id} AND association_type=${role} AND review_status='rejected') +
    (SELECT count(*) FROM podcast_candidate_reviews WHERE comedian_id=${source.comedian_id} AND (podcast_id=${target.podcast_id} OR ${candidates.length ? Prisma.join(candidates, " OR ") : Prisma.sql`FALSE`}) AND (association_type=${role} OR association_type IS NULL) AND candidate_status='rejected')
   )::int AS count`);
            if (counts.count)
                reasons.push("Legacy relationship rejection remains active.");
        }
        const a = await migrationCompatibility(tx, current.source_id),
            b = await migrationCompatibility(tx, current.target_id);
        if (a.blocked || b.blocked)
            reasons.push("An endpoint remains suppressed.");
    } else {
        const keys = await tx.$queryRaw<Row[]>(
            Prisma.sql`SELECT * FROM curation_identity_keys WHERE entity_id=${id}`,
        );
        if (current.kind === "comedian") {
            const [comedian] = await tx.$queryRaw<Row[]>(
                Prisma.sql`SELECT to_jsonb(c) AS data FROM comedians c WHERE id=${current.comedian_id}`,
            );
            const names = new Set(
                [
                    current.label,
                    comedian?.data?.name,
                    ...keys
                        .filter((k) => k.key_type === "exact_name")
                        .map((k) => k.value),
                ]
                    .filter(Boolean)
                    .map(normalizeExactNameV1),
            );
            // Use the same normalization contract as the migration; do not infer substring denials.
            const rows = await tx.$queryRaw<Row[]>(
                Prisma.sql`SELECT name,'name-denial' AS source FROM comedian_deny_list UNION ALL SELECT name,'hidden-comedian' AS source FROM comedians WHERE visible=false`,
            );
            if (rows.some((r) => names.has(normalizeExactNameV1(r.name))))
                reasons.push(
                    "Legacy comedian visibility/name suppression remains active.",
                );
            const candidateKeys = keys
                .filter((k) =>
                    k.namespace.includes(":comedian_identity_candidates:v1"),
                )
                .map((k) => k.value);
            if (candidateKeys.length) {
                const rows = await tx.$queryRaw<Row[]>(
                    Prisma.sql`SELECT uuid FROM comedian_identity_candidates WHERE uuid IN (${Prisma.join(candidateKeys)}) AND status='rejected'`,
                );
                if (rows.length)
                    reasons.push("Legacy identity rejection remains active.");
            }
        } else if (current.kind === "club") {
            const places = keys
                .filter((k) => k.namespace === "google-place:v1")
                .map((k) => k.value);
            if (
                places.length &&
                (
                    await tx.$queryRaw<Row[]>(
                        Prisma.sql`SELECT google_place_id FROM venue_deny_list WHERE google_place_id IN (${Prisma.join(places)})`,
                    )
                ).length
            )
                reasons.push("Legacy place-ID denial remains active.");
        } else if (current.kind === "podcast") {
            const clauses = [Prisma.sql`podcast_id=${current.podcast_id}`];
            for (const k of keys) {
                if (k.namespace.startsWith("provider:"))
                    clauses.push(
                        Prisma.sql`(source=${k.scope} AND source_podcast_id=${k.value})`,
                    );
                if (k.key_type === "feed_url")
                    clauses.push(Prisma.sql`feed_url=${k.value}`);
                if (k.namespace.includes(":podcast_deny_list:v1"))
                    clauses.push(Prisma.sql`id::text=${k.value}`);
            }
            if (
                (
                    await tx.$queryRaw<Row[]>(
                        Prisma.sql`SELECT id FROM podcast_deny_list WHERE restored_at IS NULL AND (${Prisma.join(clauses, " OR ")})`,
                    )
                ).length
            )
                reasons.push("Legacy podcast denial remains active.");
        }
    }
    const legacyBlocked = !!reasons.length;
    return {
        blocked:
            legacyBlocked ||
            ["blocked", "rejected", "severed"].includes(current.disposition),
        legacyBlocked,
        reasons,
        current,
    };
}
const restoreSchema = z
    .object({
        id: z.string().min(1),
        relationship: z.boolean().default(false),
        expectedVersion: z.number().int().min(1),
        actor: z.string().trim().min(1),
        reason: z.string().trim().min(1),
    })
    .strict();
/** Explicit migration reconciliation only, not a replacement for domain restoration adapters. */
export async function restoreImportedDecision(store: Store, input: unknown) {
    const x = restoreSchema.parse(input);
    return store.$transaction(async (tx) => {
        await lockMigration(tx);
        const status = await migrationCompatibility(tx, x.id, x.relationship),
            row = status.current;
        if (row.version !== x.expectedVersion)
            throw new Error("Target changed; review the latest state.");
        if (status.legacyBlocked)
            throw new Error(
                "Resolve legacy suppression first; restoration cannot bypass compatibility enforcement.",
            );
        if (!["blocked", "rejected", "severed"].includes(row.disposition))
            throw new Error("Target is not negatively decided.");
        const [last] = await tx.$queryRaw<Row[]>(
            Prisma.sql`SELECT id,evidence FROM curation_decisions WHERE ${field(x.relationship)}=${x.id} AND version=${row.version}`,
        );
        if (last?.evidence?.migration !== MIGRATION)
            throw new Error(
                "Latest decision is not migration-owned; use the authoritative review workflow.",
            );
        const after = x.relationship ? "proposed" : "pending",
            id = randomUUID();
        await tx.$queryRaw(
            Prisma.sql`INSERT INTO curation_decisions(id,${field(x.relationship)},version,action,before_state,after_state,actor,reason,evidence) VALUES(${id},${x.id},${row.version + 1},'restore',${row.disposition},${after},${x.actor},${x.reason},${JSON.stringify({ restoresMigrationDecision: last.id, legacySuppressionChecked: true })}::jsonb) RETURNING id`,
        );
        return { decisionId: id, disposition: after, version: row.version + 1 };
    });
}
