import { randomUUID } from "node:crypto";
import { Prisma } from "@prisma/client";
import { z } from "zod";
import {
    entityTransition,
    relationshipTransition,
    type EntityDisposition,
    type RelationshipDisposition,
    type EntityAction,
    type RelationshipAction,
    type ProcessingState,
} from "./contracts";

const id = z.string().trim().min(1).max(200);
export const targetSchema = z.discriminatedUnion("type", [
    z
        .object({
            type: z.literal("entity"),
            id,
            kind: z.enum(["comedian", "club", "show", "podcast"]),
            scope: z.enum(["entity", "name", "series"]),
        })
        .strict(),
    z
        .object({
            type: z.literal("relationship"),
            id,
            kind: z.enum(["alias_of", "host_of", "cohost_of"]),
        })
        .strict(),
]);
export const commandSchema = z
    .object({
        requestId: z.string().uuid(),
        target: targetSchema,
        expectedVersion: z.number().int().min(0),
        action: z.enum([
            "approve",
            "block",
            "restore",
            "confirm",
            "reject",
            "sever",
        ]),
        reason: z.string().trim().min(1).max(2000),
    })
    .strict()
    .superRefine((command, ctx) => {
        const actions =
            command.target.type === "entity"
                ? ["approve", "block", "restore"]
                : ["confirm", "reject", "sever", "restore"];
        if (!actions.includes(command.action))
            ctx.addIssue({
                code: z.ZodIssueCode.custom,
                path: ["action"],
                message: "Action does not apply to this target type.",
            });
        if (
            command.target.type === "entity" &&
            command.target.scope === "series" &&
            command.target.kind !== "show"
        )
            ctx.addIssue({
                code: z.ZodIssueCode.custom,
                path: ["target", "scope"],
                message: "Series scope requires a show.",
            });
    });
export type Command = z.infer<typeof commandSchema>;
export type Target = z.infer<typeof targetSchema>;
export type SqlClient = {
    $queryRaw<T = unknown>(query: Prisma.Sql): Promise<T>;
};
export type Store = SqlClient & {
    $transaction<T>(fn: (tx: SqlClient) => Promise<T>): Promise<T>;
};
export type Snapshot = {
    id: string;
    kind: string;
    disposition: string;
    version: number;
    identity_scope?: string;
    source_id?: string;
    target_id?: string;
};
export class CurationError extends Error {
    constructor(
        public code: string,
        message: string,
        public status = 409,
        public current?: Snapshot,
    ) {
        super(message);
    }
}
export type Adapter = {
    mode: "immediate" | "worker";
    /** Source-specific eligibility and scope checks, rerun inside the application transaction. */
    validate(
        tx: SqlClient,
        target: Target,
        snapshot: Snapshot,
        command: Command,
    ): Promise<void>;
    /** Read-only effects for preview. Never perform writes or remote side effects here. */
    preview(
        tx: SqlClient,
        target: Target,
        snapshot: Snapshot,
        command: Command,
    ): Promise<string[]>;
    /** Only transactional DB effects via tx. External work must use a transactional outbox. */
    apply(
        tx: SqlClient,
        target: Target,
        snapshot: Snapshot,
        command: Command,
    ): Promise<void>;
};
export type RequestResult = {
    id: string;
    entity_id: string | null;
    relationship_id: string | null;
    expected_version: number;
    action: Command["action"];
    actor: string;
    reason: string;
    status: ProcessingState;
    decision_id: string | null;
    error: string | null;
};
export type Dependencies = {
    store: Store;
    adapter(target: Target): Adapter | undefined;
    /** Must be retry-safe. Runs after commit, including an applied request replay. */
    invalidate(target: Target): Promise<void>;
};
const table = (target: Target) =>
    target.type === "entity"
        ? Prisma.raw("curation_entities")
        : Prisma.raw("curation_relationships");
async function snapshot(
    tx: SqlClient,
    target: Target,
    lock = false,
): Promise<Snapshot> {
    const [row] = await tx.$queryRaw<Snapshot[]>(
        Prisma.sql`SELECT * FROM ${table(target)} WHERE id=${target.id} ${lock ? Prisma.sql`FOR UPDATE` : Prisma.empty}`,
    );
    if (!row)
        throw new CurationError(
            "not_found",
            "Curation target no longer exists.",
            404,
        );
    if (
        row.kind !== target.kind ||
        (target.type === "entity" && row.identity_scope !== target.scope)
    )
        throw new CurationError(
            "target_mismatch",
            "Target kind or explicit block scope does not match the reviewed identity.",
        );
    return row;
}
function transition(row: Snapshot, command: Command) {
    if (row.version !== command.expectedVersion)
        throw new CurationError(
            "stale_version",
            "This item changed. Refresh its preview before deciding.",
            409,
            row,
        );
    try {
        if (command.target.type === "entity") {
            const next = entityTransition(
                row.disposition as EntityDisposition,
                command.action as EntityAction,
            );
            if (next === "approved" && command.target.scope !== "entity")
                throw new Error();
            return next;
        }
        return relationshipTransition(
            row.disposition as RelationshipDisposition,
            command.action as RelationshipAction,
        );
    } catch {
        throw new CurationError(
            "invalid_transition",
            "This action is unavailable. A blocked or severed item must first be explicitly restored for review.",
            409,
            row,
        );
    }
}
function requireAdapter(deps: Dependencies, target: Target) {
    const adapter = deps.adapter(target);
    if (!adapter)
        throw new CurationError(
            "adapter_unavailable",
            "This workflow is not enabled yet; continue using its existing review controls.",
            503,
        );
    return adapter;
}
function classify(error: unknown): CurationError | undefined {
    if (error instanceof CurationError) return error;
    const e = error as { code?: string; meta?: { code?: string } };
    const code = e?.meta?.code ?? e?.code;
    if (
        ["40001", "40P01", "23505", "23514", "P2034", "P2002"].includes(
            code ?? "",
        )
    )
        return new CurationError(
            "decision_conflict",
            "The decision conflicts with current state or relationship constraints. Refresh and review again.",
        );
}
export function createCurationService(deps: Dependencies) {
    async function getRequest(requestId: string): Promise<RequestResult> {
        const [row] = await deps.store.$queryRaw<RequestResult[]>(
            Prisma.sql`SELECT * FROM curation_requests WHERE id=${id.parse(requestId)}`,
        );
        if (!row)
            throw new CurationError(
                "not_found",
                "Curation request not found.",
                404,
            );
        return row;
    }
    async function targetFor(
        tx: SqlClient,
        request: RequestResult,
    ): Promise<Target> {
        if (request.entity_id) {
            const [row] = await tx.$queryRaw<Snapshot[]>(
                Prisma.sql`SELECT * FROM curation_entities WHERE id=${request.entity_id}`,
            );
            return targetSchema.parse({
                type: "entity",
                id: request.entity_id,
                kind: row?.kind,
                scope: row?.identity_scope,
            });
        }
        const [row] = await tx.$queryRaw<Snapshot[]>(
            Prisma.sql`SELECT * FROM curation_relationships WHERE id=${request.relationship_id}`,
        );
        return targetSchema.parse({
            type: "relationship",
            id: request.relationship_id,
            kind: row?.kind,
        });
    }
    async function process(requestId: string): Promise<RequestResult> {
        id.parse(requestId);
        try {
            await deps.store.$transaction(async (tx) => {
                const [request] = await tx.$queryRaw<RequestResult[]>(
                    Prisma.sql`SELECT * FROM curation_requests WHERE id=${requestId} FOR UPDATE`,
                );
                if (!request)
                    throw new CurationError(
                        "not_found",
                        "Curation request not found.",
                        404,
                    );
                if (request.status !== "pending") return;
                const target = await targetFor(tx, request),
                    adapter = requireAdapter(deps, target);
                const command: Command = {
                    requestId,
                    target,
                    expectedVersion: request.expected_version,
                    action: request.action,
                    reason: request.reason,
                };
                const row = await snapshot(tx, target, true),
                    next = transition(row, command);
                await adapter.validate(tx, target, row, command);
                await tx.$queryRaw(Prisma.sql`INSERT INTO curation_decisions(id,entity_id,relationship_id,version,action,before_state,after_state,actor,reason)
     VALUES(${randomUUID()},${request.entity_id},${request.relationship_id},${row.version + 1},${command.action},${row.disposition},${next},${request.actor},${request.reason}) RETURNING id`);
                await adapter.apply(tx, target, row, command);
                await tx.$queryRaw(
                    Prisma.sql`UPDATE curation_requests SET status='applied', completed_at=now(), decision_id=(SELECT id FROM curation_decisions WHERE version=${row.version + 1} AND entity_id IS NOT DISTINCT FROM ${request.entity_id} AND relationship_id IS NOT DISTINCT FROM ${request.relationship_id}) WHERE id=${requestId} RETURNING id`,
                );
            });
        } catch (error) {
            const conflict = classify(error);
            // Failed transactions leave no decision/domain writes. Retain a terminal receipt.
            await deps.store.$queryRaw(
                Prisma.sql`UPDATE curation_requests SET status=${conflict?.status === 409 ? "conflict" : "failed"},error=${conflict?.message ?? "Application failed; no decision was applied. Review and submit a new request."},completed_at=now() WHERE id=${requestId} AND status='pending' RETURNING id`,
            );
        }
        const result = await getRequest(requestId);
        if (result.status === "applied")
            await deps.invalidate(await targetFor(deps.store, result));
        return result;
    }
    async function preview(input: unknown) {
        const command = commandSchema.parse(input);
        return deps.store.$transaction(async (tx) => {
            const row = await snapshot(tx, command.target),
                next = transition(row, command),
                adapter = deps.adapter(command.target);
            if (adapter)
                await adapter.validate(tx, command.target, row, command);
            return {
                target: command.target,
                version: row.version,
                before: row.disposition,
                after: next,
                available: !!adapter,
                mode: adapter?.mode ?? null,
                disabledReason: adapter
                    ? null
                    : "Domain adapter is not enabled.",
                effects: adapter
                    ? await adapter.preview(tx, command.target, row, command)
                    : [],
                boundaries:
                    command.target.type === "entity"
                        ? "Only this scoped entity decision changes; relationships require separate decisions."
                        : "Only this edge changes; neither endpoint is blocked or deleted.",
                restoration:
                    "Restore reopens review. It does not approve, publish, or restore other relationships.",
            };
        });
    }
    async function submitCommand(input: unknown, actor: string) {
        const command = commandSchema.parse(input);
        id.parse(actor);
        const mode = await deps.store.$transaction(async (tx) => {
            // Immutable target kind/scope is checked even on replay.
            await snapshot(tx, command.target);
            const entityId =
                command.target.type === "entity" ? command.target.id : null;
            const relationshipId =
                command.target.type === "relationship"
                    ? command.target.id
                    : null;
            // Reserve request ID before comparing payload, serializing simultaneous retries.
            const inserted = await tx.$queryRaw<{ id: string }[]>(
                Prisma.sql`INSERT INTO curation_requests(id,entity_id,relationship_id,expected_version,action,actor,reason) VALUES(${command.requestId},${entityId},${relationshipId},${command.expectedVersion},${command.action},${actor},${command.reason}) ON CONFLICT(id) DO NOTHING RETURNING id`,
            );
            const [request] = await tx.$queryRaw<RequestResult[]>(
                Prisma.sql`SELECT * FROM curation_requests WHERE id=${command.requestId} FOR UPDATE`,
            );
            if (
                request.entity_id !== entityId ||
                request.relationship_id !== relationshipId ||
                request.expected_version !== command.expectedVersion ||
                request.action !== command.action ||
                request.actor !== actor ||
                request.reason !== command.reason
            )
                throw new CurationError(
                    "idempotency_conflict",
                    "This request ID was used for another decision. Refresh and use a new request ID.",
                );
            if (request.status !== "pending") return "replay";
            // A replay reports the original receipt even if eligibility has since changed.
            // An interrupted immediate command is safely resumed by process().
            if (!inserted.length)
                return deps.adapter(command.target)?.mode === "immediate"
                    ? "immediate"
                    : "replay";
            const adapter = requireAdapter(deps, command.target);
            const row = await snapshot(tx, command.target, true);
            transition(row, command);
            await adapter.validate(tx, command.target, row, command);
            return adapter.mode;
        });
        if (mode === "immediate") return process(command.requestId);
        const result = await getRequest(command.requestId);
        if (result.status === "applied") await deps.invalidate(command.target);
        return result;
    }
    async function submit(input: unknown, actor: string) {
        try {
            return await submitCommand(input, actor);
        } catch (error) {
            throw classify(error) ?? error;
        }
    }
    return { preview, submit, getRequest, process };
}
