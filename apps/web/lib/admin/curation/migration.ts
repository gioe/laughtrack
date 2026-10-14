import { createHash } from "node:crypto";
import { Prisma } from "@prisma/client";
import { z } from "zod";
import { normalizeExactNameV1, type EntityKind } from "./contracts";
import type { SqlClient, Store } from "./decisions";
export const MIGRATION = "legacy-curation:v1";
export const sources = [
    "comedians",
    "comedian_deny_list",
    "clubs",
    "venue_deny_list",
    "podcast_deny_list",
    "comedian_identity_candidates",
    "comedian_podcasts",
    "podcast_candidate_reviews",
    "comedy_event_reviews",
] as const;
export type Source = (typeof sources)[number];
type Row = Record<string, any>;
type Key = { namespace: string; scope: string; value: string; keyType: string };
type Entity = {
    ref: string;
    kind: EntityKind;
    scope: "entity" | "name";
    label: string;
    domainId?: number;
    keys: Key[];
    desired?: "blocked" | "approved" | "restored";
    actor?: string;
    reason?: string;
    at?: string;
    restoreActor?: string;
    restoreAt?: string;
};
type Edge = {
    kind: "alias_of" | "host_of" | "cohost_of";
    source: string;
    target: string;
    desired?: "rejected" | "confirmed";
    actor?: string;
    reason?: string;
    at?: string;
};
export type Item = {
    source: Source;
    key: string;
    raw: Row;
    context: Row;
    entities: Entity[];
    edge?: Edge;
    notes: string[];
    conflicts: string[];
    fingerprint: string;
};
export const optionsSchema = z
    .object({
        source: z.enum(sources),
        after: z.string().max(500).default(""),
        limit: z.number().int().min(1).max(50).default(10),
        environment: z.string().regex(/^[a-z0-9][a-z0-9_.-]{0,63}$/),
    })
    .strict();
type Options = z.infer<typeof optionsSchema>;
export type Plan = {
    version: typeof MIGRATION;
    options: Options;
    items: Item[];
    nextCursor: string | null;
    digest: string;
};
function stable(value: unknown): string {
    if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
    if (value && typeof value === "object")
        return `{${Object.entries(value)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([k, v]) => `${JSON.stringify(k)}:${stable(v)}`)
            .join(",")}}`;
    return JSON.stringify(value) ?? "null";
}
const hash = (v: unknown) =>
    createHash("sha256").update(stable(v)).digest("hex");
const identity = (e: Entity) =>
    `legacy-${hash([e.kind, e.scope, e.keys[0]]).slice(0, 40)}`;
const rawId = (source: Source) =>
    source === "comedian_deny_list"
        ? "name"
        : source === "venue_deny_list"
          ? "google_place_id"
          : source === "comedian_identity_candidates"
            ? "uuid"
            : "id";
const identifier = (name: string) => Prisma.raw(`"${name}"`); // only fixed source/column constants below
async function query(
    tx: SqlClient,
    table: string,
    where: Prisma.Sql = Prisma.sql`TRUE`,
) {
    const rows = await tx.$queryRaw<{ row: Row }[]>(
        Prisma.sql`SELECT to_jsonb(t) AS row FROM ${identifier(table)} t WHERE ${where} ORDER BY to_jsonb(t)::text LIMIT 5001`,
    );
    if (rows.length > 5000)
        throw new Error(
            "Legacy context exceeds the 5000-row safety limit; review this record separately.",
        );
    return rows.map((x) => x.row);
}
async function one(tx: SqlClient, table: string, id: unknown) {
    return (await query(tx, table, Prisma.sql`id=${id}`))[0];
}
export const providerKey = (source: string, id: string): Key => ({
    namespace: `provider:${hash(source).slice(0, 24)}:v1`,
    scope: source,
    value: id,
    keyType: "external_id",
});
export function legacyKey(
    environment: string,
    table: string,
    id: unknown,
): Key {
    return {
        namespace: `legacy:${environment}:${table}:v1`,
        scope: "global",
        value: String(id),
        keyType: "legacy_id",
    };
}
function domainEntity(kind: EntityKind, row: Row, environment: string): Entity {
    const table = {
        comedian: "comedians",
        club: "clubs",
        show: "shows",
        podcast: "podcasts",
    }[kind];
    const e: Entity = {
        ref: `${kind}:${row.id}`,
        kind,
        scope: "entity",
        label: row.name ?? row.title ?? `${kind} ${row.id}`,
        domainId: row.id,
        keys: [legacyKey(environment, table, row.id)],
    };
    if (kind === "comedian" && row.uuid)
        e.keys.push(legacyKey(environment, "comedian_uuid", row.uuid));
    if (kind === "club" && row.google_place_id)
        e.keys.push({
            namespace: "google-place:v1",
            scope: "global",
            value: row.google_place_id,
            keyType: "external_id",
        });
    if (kind === "podcast") {
        if (row.source && row.source_podcast_id)
            e.keys.push(providerKey(row.source, row.source_podcast_id));
        if (row.feed_url)
            e.keys.push({
                namespace: "podcast-feed:exact:v1",
                scope: "global",
                value: row.feed_url,
                keyType: "feed_url",
            });
    }
    return e;
}
function nameRule(name: string): Entity {
    const value = normalizeExactNameV1(name);
    return {
        ref: `name:${value}`,
        kind: "comedian",
        scope: "name",
        label: name,
        keys: [
            {
                namespace: "exact-name:v1",
                scope: "global",
                value,
                keyType: "exact_name",
            },
        ],
    };
}
function negative(
    e: Entity,
    row: Row,
    actor: string,
    reason: string,
    at: string,
) {
    e.desired = "blocked";
    e.actor = row[actor];
    e.reason = row[reason];
    e.at = row[at];
}
function proofMatches(proof: Row | undefined, row: Row) {
    const after = proof?.after_json?.row;
    if (
        !after ||
        !row.reviewed_by ||
        proof?.actor !== row.reviewed_by ||
        !row.reviewed_at ||
        !after.reviewed_at
    )
        return false;
    if (
        new Date(row.reviewed_at).getTime() !==
        new Date(after.reviewed_at).getTime()
    )
        return false;
    return [
        "id",
        "uuid",
        "version",
        "canonical_comedian_id",
        "comedian_id",
        "podcast_id",
        "association_type",
        "review_status",
        "status",
    ].every((k) => after[k] === row[k]);
}
async function prepare(
    tx: SqlClient,
    source: Source,
    row: Row,
    environment: string,
): Promise<Item> {
    const item: Item = {
        source,
        key: String(row[rawId(source)]),
        raw: row,
        context: {},
        entities: [],
        notes: [],
        conflicts: [],
        fingerprint: "",
    };
    const add = (kind: EntityKind, r: Row) => {
        const e = domainEntity(kind, r, environment);
        item.entities.push(e);
        return e;
    };
    const auditWorkflow =
        source === "comedian_identity_candidates"
            ? "comedian_identity"
            : source === "comedian_podcasts"
              ? "podcast_association"
              : source === "comedians"
                ? "comedian_visibility"
                : source === "clubs"
                  ? "club_visibility"
                  : null;
    const audits = auditWorkflow
        ? await query(
              tx,
              "admin_review_decisions",
              Prisma.sql`workflow=${auditWorkflow} AND item_id=${item.key}`,
          )
        : [];
    item.context.audit = audits;
    const proof = audits
        .filter((a) => !a.undone_at && a.action === "approve")
        .sort((a, b) =>
            String(b.created_at).localeCompare(String(a.created_at)),
        )[0];
    if (source === "comedians") {
        const e = add("comedian", row);
        if (row.visible === false) {
            negative(
                e,
                row,
                "block_added_by",
                "block_reason",
                "block_added_at",
            );
            const rule = nameRule(row.name);
            negative(
                rule,
                row,
                "block_added_by",
                "block_reason",
                "block_added_at",
            );
            item.entities.push(rule);
        } else
            item.notes.push(
                "Visibility or validation flags alone do not manufacture approval.",
            );
        if (row.parent_comedian_id) {
            const parent = await one(tx, "comedians", row.parent_comedian_id);
            item.context.parent = parent ?? null;
            if (!parent || parent.id === row.id)
                item.conflicts.push(
                    "Missing or self parent requires manual reconciliation.",
                );
            else {
                const p = add("comedian", parent);
                item.edge = { kind: "alias_of", source: e.ref, target: p.ref };
                item.notes.push(
                    "Existing parent link retained as a proposal; human attribution is not available.",
                );
            }
        }
    } else if (source === "comedian_deny_list") {
        const e = nameRule(row.name);
        negative(e, row, "added_by", "reason", "deleted_at");
        item.entities.push(e);
    } else if (source === "clubs") {
        add("club", row);
        item.notes.push(
            "Club visibility is publication/routing state, never proof of a permanent rejection.",
        );
    } else if (source === "venue_deny_list") {
        const matches = await query(
            tx,
            "clubs",
            Prisma.sql`google_place_id=${row.google_place_id}`,
        );
        item.context.clubs = matches;
        if (matches.length > 1)
            item.conflicts.push("Place ID resolves to multiple clubs.");
        const e =
            matches.length === 1
                ? add("club", matches[0])
                : {
                      ref: `place:${row.google_place_id}`,
                      kind: "club" as const,
                      scope: "entity" as const,
                      label: row.name,
                      keys: [
                          {
                              namespace: "google-place:v1",
                              scope: "global",
                              value: row.google_place_id,
                              keyType: "external_id",
                          },
                      ],
                  };
        if (!item.entities.includes(e)) item.entities.push(e);
        negative(e, row, "added_by", "reason", "denied_at");
    } else if (source === "podcast_deny_list") {
        const matches = await query(
            tx,
            "podcasts",
            Prisma.sql`id=${row.podcast_id ?? null} OR (source=${row.source ?? null} AND source_podcast_id=${row.source_podcast_id ?? null}) OR feed_url=${row.feed_url ?? null}`,
        );
        item.context.podcasts = matches;
        if (matches.length > 1)
            item.conflicts.push(
                "Podcast denial keys resolve to different public identities.",
            );
        const e =
            matches.length === 1
                ? add("podcast", matches[0])
                : {
                      ref: `podcast-denial:${row.id}`,
                      kind: "podcast" as const,
                      scope: "entity" as const,
                      label: `Denied podcast ${row.id}`,
                      keys: [
                          legacyKey(environment, "podcast_deny_list", row.id),
                      ],
                  };
        if (!item.entities.includes(e)) item.entities.push(e);
        if (row.source && row.source_podcast_id)
            e.keys.push(providerKey(row.source, row.source_podcast_id));
        if (row.feed_url)
            e.keys.push({
                namespace: "podcast-feed:exact:v1",
                scope: "global",
                value: row.feed_url,
                keyType: "feed_url",
            });
        negative(e, row, "denied_by", "reason", "denied_at");
        if (row.restored_at) {
            e.desired = "restored";
            e.restoreActor = row.restored_by;
            e.restoreAt = row.restored_at;
            item.notes.push(
                "Historical denial/restoration is retained; restore returns to pending, not approved.",
            );
        }
    } else if (source === "comedian_identity_candidates") {
        const canonical = row.canonical_comedian_id
            ? await one(tx, "comedians", row.canonical_comedian_id)
            : null;
        item.context.canonical = canonical;
        item.context.evidence = await query(
            tx,
            "comedian_identity_evidence",
            Prisma.sql`candidate_uuid=${row.uuid}`,
        );
        const e: Entity = {
            ref: `candidate:${row.uuid}`,
            kind: "comedian",
            scope: "entity",
            label: row.name,
            keys: [
                legacyKey(
                    environment,
                    "comedian_identity_candidates",
                    row.uuid,
                ),
            ],
        };
        // Link only when the retained audit agrees with the candidate's current target.
        if (
            canonical &&
            row.status === "accepted" &&
            proofMatches(proof, row) &&
            proof?.after_json?.row?.canonical_comedian_id === canonical.id
        ) {
            const c = add("comedian", canonical);
            c.keys.push(...e.keys);
            c.desired = "approved";
            c.actor = proof.actor;
            c.reason = proof.reason;
            c.at = proof.created_at;
        } else {
            item.entities.push(e);
            if (row.status === "rejected")
                negative(e, row, "reviewed_by", "reason", "reviewed_at");
            else
                item.notes.push(
                    "Unproven or linked candidate remains pending; no inferred approval or merge.",
                );
        }
    } else if (
        source === "comedian_podcasts" ||
        source === "podcast_candidate_reviews"
    ) {
        const comedian = await one(tx, "comedians", row.comedian_id);
        const podcasts = await query(
            tx,
            "podcasts",
            Prisma.sql`id=${row.podcast_id ?? null} OR (source=${row.source} AND source_podcast_id=${row.source_podcast_id ?? null})`,
        );
        item.context.comedian = comedian ?? null;
        item.context.podcasts = podcasts;
        const associations = await query(
            tx,
            "comedian_podcasts",
            Prisma.sql`comedian_id=${row.comedian_id} AND podcast_id=${row.podcast_id ?? podcasts[0]?.id ?? null}`,
        );
        const candidates = await query(
            tx,
            "podcast_candidate_reviews",
            Prisma.sql`comedian_id=${row.comedian_id} AND (podcast_id=${row.podcast_id ?? podcasts[0]?.id ?? null} OR (source=${row.source} AND source_podcast_id=${row.source_podcast_id ?? null}))`,
        );
        item.context.associations = associations;
        item.context.candidates = candidates;
        if (
            !comedian ||
            podcasts.length > 1 ||
            (source === "comedian_podcasts" && podcasts.length === 0)
        )
            item.conflicts.push(
                "Missing comedian or ambiguous podcast identity.",
            );
        if (comedian) {
            const c = add("comedian", comedian);
            const p =
                podcasts.length === 1
                    ? add("podcast", podcasts[0])
                    : {
                          ref: `podcast-candidate:${row.id}`,
                          kind: "podcast" as const,
                          scope: "entity" as const,
                          label: `Podcast candidate ${row.source_podcast_id}`,
                          keys: [
                              providerKey(row.source, row.source_podcast_id),
                          ],
                      };
            if (!item.entities.includes(p)) item.entities.push(p);
            if (!["host", "cohost"].includes(row.association_type))
                item.conflicts.push(
                    "Unknown or unsupported relationship role requires review.",
                );
            else {
                const relevant = [...associations, ...candidates].filter(
                    (a) => a.association_type === row.association_type,
                );
                const states = new Set(
                    relevant.map((a) => a.review_status ?? a.candidate_status),
                );
                const edge: Edge = {
                    kind:
                        row.association_type === "host"
                            ? "host_of"
                            : "cohost_of",
                    source: c.ref,
                    target: p.ref,
                };
                item.edge = edge;
                if (states.has("rejected") && states.has("accepted"))
                    item.conflicts.push(
                        "Conflicting source-specific relationship decisions; retain legacy enforcement and review before unifying.",
                    );
                else if (
                    (row.review_status ?? row.candidate_status) === "rejected"
                ) {
                    edge.desired = "rejected";
                    edge.actor = row.reviewed_by;
                    edge.at = row.reviewed_at;
                    edge.reason =
                        "Legacy relationship rejection (original evidence retained).";
                } else if (
                    row.review_status === "accepted" &&
                    proofMatches(proof, row) &&
                    proof?.after_json?.row?.review_status === "accepted"
                ) {
                    edge.desired = "confirmed";
                    edge.actor = proof.actor;
                    edge.at = proof.created_at;
                    edge.reason = proof.reason;
                } else
                    item.notes.push(
                        "Accepted/pending source link is evidence only without a matching admin audit.",
                    );
            }
        }
    } else {
        const candidate = await one(
                tx,
                "comedy_event_candidates",
                row.candidate_id,
            ),
            decision = await one(tx, "comedy_event_decisions", row.decision_id);
        item.context.candidate = candidate ?? null;
        item.context.decision = decision ?? null;
        item.context.observations = await query(
            tx,
            "comedy_event_observations",
            Prisma.sql`candidate_id=${row.candidate_id} AND generation=${row.observation_generation}`,
        );
        item.context.publications = await query(
            tx,
            "comedy_event_publications",
            Prisma.sql`candidate_id=${row.candidate_id} AND decision_id=${row.decision_id}`,
        );
        if (!candidate) item.conflicts.push("Event candidate is missing.");
        else
            item.entities.push({
                ref: `event:${candidate.id}`,
                kind: "show",
                scope: "entity",
                label: decision?.payload?.name ?? `Event ${candidate.id}`,
                keys: [
                    legacyKey(
                        environment,
                        "comedy_event_candidates",
                        candidate.id,
                    ),
                    {
                        namespace: `legacy:${environment}:event-key:v1`,
                        scope: String(candidate.source_id),
                        value: candidate.event_key,
                        keyType: "external_id",
                    },
                ],
            });
        item.notes.push(
            "Scoped event review retained as evidence only. Payload, identity, policy and observation scope are not permanent occurrence/series decisions.",
        );
    }
    item.context.domainAudits = [];
    item.context.identityMatches = [];
    for (const e of item.entities) {
        if (e.domainId)
            item.context.domainAudits.push(
                ...(await query(
                    tx,
                    "admin_action_audits",
                    Prisma.sql`entity_type=${e.kind} AND entity_id=${String(e.domainId)}`,
                )),
            );
        if (e.kind === "club") {
            for (const key of e.keys.filter(
                (k) => k.namespace === "google-place:v1",
            )) {
                const matches = await query(
                    tx,
                    "clubs",
                    Prisma.sql`google_place_id=${key.value}`,
                );
                item.context.identityMatches.push(...matches);
                if (matches.length > 1)
                    item.conflicts.push(
                        "Place identity is ambiguous across existing clubs.",
                    );
            }
        }
        if (e.kind === "podcast") {
            for (const key of e.keys.filter((k) => k.keyType === "feed_url")) {
                const matches = await query(
                    tx,
                    "podcasts",
                    Prisma.sql`feed_url=${key.value}`,
                );
                item.context.identityMatches.push(...matches);
                if (matches.length > 1)
                    item.conflicts.push(
                        "Feed identity is ambiguous across existing podcasts.",
                    );
            }
        }
        if (e.desired === "approved" && e.kind === "comedian") {
            const denied = await query(
                tx,
                "comedian_deny_list",
                Prisma.sql`lower(btrim(regexp_replace(replace(name,chr(160),' '),'[[:space:]]+',' ','g')))=lower(btrim(regexp_replace(replace(${e.label},chr(160),' '),'[[:space:]]+',' ','g')))`,
            );
            item.context.identityDenials = denied;
            if (
                item.context.canonical?.visible === false ||
                item.context.canonical?.parent_comedian_id != null ||
                denied.length
            )
                item.conflicts.push(
                    "Legacy suppression conflicts with historical identity approval.",
                );
        }
    }
    if (
        source === "comedian_podcasts" &&
        row.review_status === "accepted" &&
        item.edge &&
        !item.edge.desired &&
        !item.conflicts.length
    ) {
        const audit = item.context.domainAudits.find(
            (a: Row) =>
                a.action === "podcast_hostship_review.approve" &&
                a.actor_profile_id &&
                a.actor_profile_id === row.reviewed_by &&
                a.after_json?.hostships?.some(
                    (h: Row) =>
                        h.id === row.id &&
                        h.comedianId === row.comedian_id &&
                        h.podcastId === row.podcast_id &&
                        h.associationType === row.association_type &&
                        h.source === row.source &&
                        h.reviewStatus === "accepted" &&
                        h.reviewedBy === row.reviewed_by &&
                        row.reviewed_at &&
                        h.reviewedAt &&
                        new Date(h.reviewedAt).getTime() ===
                            new Date(row.reviewed_at).getTime(),
                ),
        );
        if (audit) {
            item.edge.desired = "confirmed";
            item.edge.actor = audit.actor_profile_id;
            item.edge.reason = audit.reason;
            item.edge.at = audit.created_at;
            item.notes.push(
                "Current hostship matches the retained ownership-review audit.",
            );
        }
    }
    item.fingerprint = hash({
        source,
        key: item.key,
        row,
        context: item.context,
    });
    return item;
}
export async function planMigration(
    tx: SqlClient,
    input: unknown,
): Promise<Plan> {
    const options = optionsSchema.parse(input),
        column = identifier(rawId(options.source));
    const raw = await tx.$queryRaw<{ row: Row }[]>(
        Prisma.sql`SELECT to_jsonb(t) AS row FROM ${identifier(options.source)} t WHERE ${column}::text COLLATE "C">${options.after} ORDER BY ${column}::text COLLATE "C" LIMIT ${options.limit + 1}`,
    );
    const items: Item[] = [];
    for (const { row } of raw.slice(0, options.limit))
        items.push(await prepare(tx, options.source, row, options.environment));
    const plan: Omit<Plan, "digest"> = {
        version: MIGRATION,
        options,
        items,
        nextCursor:
            raw.length > options.limit ? items[items.length - 1].key : null,
    };
    if (stable(plan).length > 10_000_000)
        throw new Error("Plan exceeds the 10 MB safety limit; reduce --limit.");
    return { ...plan, digest: hash(plan) };
}
async function existing(tx: SqlClient, e: Entity): Promise<string | null> {
    const owners = new Set<string>();
    for (const key of e.keys) {
        const rows = await tx.$queryRaw<
            { entity_id: string; key_type: string; identity_scope: string }[]
        >(
            Prisma.sql`SELECT entity_id,key_type,identity_scope FROM curation_identity_keys WHERE entity_kind=${e.kind} AND namespace=${key.namespace} AND scope=${key.scope} AND value=${key.value}`,
        );
        for (const row of rows) {
            if (row.key_type !== key.keyType || row.identity_scope !== e.scope)
                throw new Error("Identity key contract mismatch.");
            owners.add(row.entity_id);
        }
    }
    if (e.domainId) {
        const column = identifier(`${e.kind}_id`);
        const rows = await tx.$queryRaw<{ id: string }[]>(
            Prisma.sql`SELECT id FROM curation_entities WHERE ${column}=${e.domainId}`,
        );
        for (const row of rows) owners.add(row.id);
    }
    if (owners.size > 1)
        throw new Error(
            "Identity keys/projection have multiple owners; no silent merge allowed.",
        );
    const id = [...owners][0] ?? null;
    if (id) {
        const [row] = await tx.$queryRaw<Row[]>(
            Prisma.sql`SELECT * FROM curation_entities WHERE id=${id}`,
        );
        if (
            row.kind !== e.kind ||
            row.identity_scope !== e.scope ||
            (e.domainId &&
                row[`${e.kind}_id`] &&
                row[`${e.kind}_id`] !== e.domainId)
        )
            throw new Error(
                "Identity type, scope or public binding conflicts with the import.",
            );
    }
    return id;
}
async function ensureEntity(tx: SqlClient, e: Entity) {
    const found = await existing(tx, e),
        id = found ?? identity(e);
    if (!found)
        await tx.$queryRaw(
            Prisma.sql`INSERT INTO curation_entities(id,kind,identity_scope,label) VALUES(${id},${e.kind},${e.scope},${e.label}) RETURNING id`,
        );
    const [row] = await tx.$queryRaw<Row[]>(
        Prisma.sql`SELECT * FROM curation_entities WHERE id=${id} FOR UPDATE`,
    );
    if (row.kind !== e.kind || row.identity_scope !== e.scope)
        throw new Error("Identity type/scope conflict.");
    if (e.domainId) {
        const field = `${e.kind}_id`;
        if (row[field] && row[field] !== e.domainId)
            throw new Error("Identity is bound to another domain record.");
        await tx.$queryRaw(
            Prisma.sql`UPDATE curation_entities SET ${identifier(field)}=${e.domainId} WHERE id=${id} RETURNING id`,
        );
    }
    for (const key of e.keys)
        await tx.$queryRaw(
            Prisma.sql`INSERT INTO curation_identity_keys(id,entity_id,entity_kind,identity_scope,key_type,namespace,scope,value) VALUES(${`key-${hash([e.kind, key.namespace, key.scope, key.value])}`},${id},${e.kind},${e.scope},${key.keyType},${key.namespace},${key.scope},${key.value}) ON CONFLICT(entity_kind,namespace,scope,value) DO NOTHING RETURNING id`,
        );
    return id;
}
async function recordState(
    tx: SqlClient,
    targetId: string,
    relationship: boolean,
    desired: string | undefined,
    meta: {
        actor?: string;
        reason?: string;
        at?: string;
        restoreActor?: string;
        restoreAt?: string;
    },
    item: Item,
    operator: string,
) {
    if (!desired) return;
    const table = identifier(
            relationship ? "curation_relationships" : "curation_entities",
        ),
        field = identifier(relationship ? "relationship_id" : "entity_id");
    const [row] = await tx.$queryRaw<Row[]>(
        Prisma.sql`SELECT * FROM ${table} WHERE id=${targetId} FOR UPDATE`,
    );
    const expected = desired === "restored" ? "pending" : desired;
    if (
        row.disposition === expected &&
        !(desired === "restored" && row.version === 0)
    )
        return;
    if (row.version > 0) {
        const [last] = await tx.$queryRaw<Row[]>(
            Prisma.sql`SELECT evidence FROM curation_decisions WHERE ${field}=${targetId} AND version=${row.version}`,
        );
        if (last?.evidence?.migration !== MIGRATION)
            throw new Error(
                "Newer non-migration decision is authoritative; hold for reconciliation.",
            );
        // Never use positive legacy drift to clear an existing negative decision.
        if (!["blocked", "rejected"].includes(desired))
            throw new Error(
                "Positive/restored legacy drift requires explicit restoration review.",
            );
    }
    const action =
        desired === "blocked" || desired === "restored"
            ? "block"
            : desired === "approved"
              ? "approve"
              : desired === "confirmed"
                ? "confirm"
                : "reject";
    const after = desired === "restored" ? "blocked" : desired;
    const evidence = JSON.stringify({
        migration: MIGRATION,
        source: item.source,
        key: item.key,
        fingerprint: item.fingerprint,
        operator,
        originalAt: meta.at ?? null,
        attribution: meta.actor ? "legacy-record" : "unattributed-legacy",
    });
    await tx.$queryRaw(
        Prisma.sql`INSERT INTO curation_decisions(id,${field},version,action,before_state,after_state,actor,reason,evidence,created_at) VALUES(${`decision-${hash([targetId, item.fingerprint, row.version + 1])}`},${targetId},${row.version + 1},${action},${row.disposition},${after},${meta.actor || "legacy:unattributed"},${meta.reason?.trim() || "Legacy decision; original reason was not recorded."},${evidence}::jsonb,COALESCE(${meta.at ?? null}::timestamptz,now())) RETURNING id`,
    );
    if (desired === "restored")
        await tx.$queryRaw(
            Prisma.sql`INSERT INTO curation_decisions(id,${field},version,action,before_state,after_state,actor,reason,evidence,created_at) VALUES(${`decision-${hash([targetId, item.fingerprint, row.version + 2])}`},${targetId},${row.version + 2},'restore','blocked','pending',${meta.restoreActor || "legacy:unattributed"},'Historical podcast restoration; reopened for review.',${evidence}::jsonb,${meta.restoreAt}::timestamptz) RETURNING id`,
        );
}
async function observation(
    tx: SqlClient,
    id: string,
    relationship: boolean,
    item: Item,
    operator: string,
) {
    const field = identifier(relationship ? "relationship_id" : "entity_id");
    await tx.$queryRaw(
        Prisma.sql`INSERT INTO curation_observations(id,${field},source,source_key,fingerprint,evidence,observed_at) VALUES(${`observation-${hash([id, item.source, item.key, item.fingerprint])}`},${id},${MIGRATION},${`${item.source}:${item.key}`},${item.fingerprint},${JSON.stringify({ raw: item.raw, context: item.context, notes: item.notes, operator, migration: MIGRATION })}::jsonb,now()) ON CONFLICT DO NOTHING RETURNING id`,
    );
}
export async function inspectMigration(tx: SqlClient, plan: Plan) {
    const results = [];
    for (const item of plan.items) {
        const conflicts = [...item.conflicts];
        for (const e of item.entities)
            try {
                const id = await existing(tx, e);
                if (id && e.desired) {
                    const [state] = await tx.$queryRaw<Row[]>(
                        Prisma.sql`SELECT disposition,version FROM curation_entities WHERE id=${id}`,
                    );
                    const desired =
                        e.desired === "restored" ? "pending" : e.desired;
                    if (state.version > 0 && state.disposition !== desired) {
                        const [last] = await tx.$queryRaw<Row[]>(
                            Prisma.sql`SELECT evidence FROM curation_decisions WHERE entity_id=${id} AND version=${state.version}`,
                        );
                        if (
                            last?.evidence?.migration !== MIGRATION ||
                            e.desired !== "blocked"
                        )
                            conflicts.push(
                                "Current curation decision requires explicit reconciliation; import will not overwrite it.",
                            );
                    }
                }
            } catch (error) {
                conflicts.push((error as Error).message);
            }
        const imported = await tx.$queryRaw<{ count: number }[]>(
            Prisma.sql`SELECT count(*)::int AS count FROM curation_observations WHERE source=${MIGRATION} AND source_key=${`${item.source}:${item.key}`} AND fingerprint=${item.fingerprint}`,
        );
        results.push({
            key: item.key,
            conflicts,
            alreadyImported: imported[0].count > 0,
            notes: item.notes,
            entityCount: item.entities.length,
            relationship: !!item.edge,
        });
    }
    return {
        source: plan.options.source,
        scanned: results.length,
        held: results.filter((r) => r.conflicts.length).length,
        alreadyImported: results.filter((r) => r.alreadyImported).length,
        items: results,
    };
}
export async function applyMigration(
    store: Store,
    saved: Plan,
    operator: string,
) {
    z.string().trim().min(1).max(200).parse(operator);
    optionsSchema.parse(saved.options);
    if (saved.version !== MIGRATION || !saved.digest)
        throw new Error("Unsupported migration plan.");
    return store.$transaction(async (tx) => {
        await lockMigration(tx);
        const current = await planMigration(tx, saved.options);
        if (current.digest !== saved.digest)
            throw new Error(
                "Legacy snapshot changed. Generate and review a fresh dry-run plan.",
            );
        const report: {
            key: string;
            status: "imported" | "skipped" | "held";
            reason?: string;
        }[] = [];
        for (const item of current.items) {
            if (item.conflicts.length) {
                report.push({
                    key: item.key,
                    status: "held",
                    reason: item.conflicts.join(" "),
                });
                continue;
            }
            const seen = await tx.$queryRaw<Row[]>(
                Prisma.sql`SELECT id FROM curation_observations WHERE source=${MIGRATION} AND source_key=${`${item.source}:${item.key}`} AND fingerprint=${item.fingerprint} LIMIT 1`,
            );
            if (seen.length) {
                report.push({ key: item.key, status: "skipped" });
                continue;
            }
            await tx.$queryRaw(Prisma.sql`SAVEPOINT curation_import_item`);
            try {
                const ids = new Map<string, string>();
                for (const e of item.entities) {
                    const id = await ensureEntity(tx, e);
                    ids.set(e.ref, id);
                    await recordState(
                        tx,
                        id,
                        false,
                        e.desired,
                        e,
                        item,
                        operator,
                    );
                    await observation(tx, id, false, item, operator);
                }
                if (item.edge) {
                    const e = item.edge,
                        source = ids.get(e.source)!,
                        target = ids.get(e.target)!;
                    const [found] = await tx.$queryRaw<Row[]>(
                        Prisma.sql`SELECT id FROM curation_relationships WHERE kind=${e.kind} AND source_id=${source} AND target_id=${target}`,
                    );
                    const id =
                        found?.id ?? `edge-${hash([e.kind, source, target])}`;
                    if (!found)
                        await tx.$queryRaw(
                            Prisma.sql`INSERT INTO curation_relationships(id,kind,source_id,target_id,target_kind) VALUES(${id},${e.kind},${source},${target},${e.kind === "alias_of" ? "comedian" : "podcast"}) RETURNING id`,
                        );
                    await recordState(
                        tx,
                        id,
                        true,
                        e.desired,
                        e,
                        item,
                        operator,
                    );
                    await observation(tx, id, true, item, operator);
                }
                report.push({ key: item.key, status: "imported" });
            } catch (error) {
                await tx.$queryRaw(
                    Prisma.sql`ROLLBACK TO SAVEPOINT curation_import_item`,
                );
                report.push({
                    key: item.key,
                    status: "held",
                    reason: (error as Error).message,
                });
            }
            await tx.$queryRaw(
                Prisma.sql`RELEASE SAVEPOINT curation_import_item`,
            );
        }
        return {
            digest: current.digest,
            nextCursor: current.nextCursor,
            imported: report.filter((r) => r.status === "imported").length,
            skipped: report.filter((r) => r.status === "skipped").length,
            held: report.filter((r) => r.status === "held").length,
            items: report,
        };
    });
}

export async function lockMigration(tx: SqlClient) {
    await tx.$queryRaw(Prisma.sql`SET LOCAL lock_timeout='3s'`);
    // Brief bounded maintenance lock protects the saved snapshot, including dependency phantoms.
    await tx.$queryRaw(
        Prisma.sql`LOCK TABLE comedians,clubs,shows,podcasts,comedian_deny_list,venue_deny_list,podcast_deny_list,comedian_identity_candidates,comedian_identity_evidence,comedian_podcasts,podcast_candidate_reviews,comedy_event_candidates,comedy_event_decisions,comedy_event_reviews,comedy_event_observations,comedy_event_publications,admin_review_decisions,admin_action_audits IN SHARE MODE`,
    );
    await tx.$queryRaw(
        Prisma.sql`LOCK TABLE curation_entities,curation_identity_keys,curation_relationships,curation_decisions,curation_observations IN SHARE ROW EXCLUSIVE MODE`,
    );
}
