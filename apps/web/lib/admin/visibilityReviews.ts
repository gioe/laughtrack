import { createHash } from "node:crypto";
import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import { ReviewConflict } from "./reviewErrors";
import type {
    ReviewItem,
    ReviewPage,
    ReviewSubmission,
    ReviewResult,
} from "./reviewTypes";

export type VisibilityWorkflow = "comedian_visibility" | "club_visibility";
type Tx = Pick<Prisma.TransactionClient, "$queryRaw">;
type Snapshot = {
    id: number;
    name: string;
    visible: boolean;
    website: string | null;
    total_shows: number;
    revision: number;
    parent_comedian_id?: number | null;
    block_reason?: string | null;
    block_added_by?: string | null;
    block_added_at?: string | null;
    address?: string;
    status?: string;
    club_type?: string;
    closed_at?: string | null;
};
function config(workflow: VisibilityWorkflow) {
    return workflow === "comedian_visibility"
        ? {
              table: Prisma.sql`comedians`,
              entity: "comedian",
              columns: Prisma.sql`c.parent_comedian_id,c.block_reason,c.block_added_by,c.block_added_at`,
          }
        : {
              table: Prisma.sql`clubs`,
              entity: "club",
              columns: Prisma.sql`c.address,c.status,c.club_type,c.closed_at`,
          };
}
function idNumber(id: string) {
    if (!/^[1-9]\d*$/.test(id) || Number(id) > 2147483647)
        throw new ReviewConflict("Invalid review item ID.");
    return Number(id);
}
function token(row: Snapshot) {
    return createHash("sha256").update(JSON.stringify(row)).digest("hex");
}
async function snapshot(tx: Tx, workflow: VisibilityWorkflow, id: number) {
    const c = config(workflow);
    const rows = await tx.$queryRaw<
        Snapshot[]
    >(Prisma.sql`SELECT c.id,c.name,c.visible,c.website,c.total_shows,${c.columns},
        COALESCE((SELECT max(a.id) FROM admin_action_audits a WHERE a.entity_type=${c.entity} AND a.entity_id=c.id::text),0) AS revision
        FROM ${c.table} c WHERE c.id=${id}`);
    return rows[0] ? (JSON.parse(JSON.stringify(rows[0])) as Snapshot) : null;
}
function item(row: Snapshot, workflow: VisibilityWorkflow): ReviewItem {
    const comic = workflow === "comedian_visibility";
    return {
        id: String(row.id),
        workflow,
        title: row.name,
        subtitle: `ID ${row.id} · ${row.visible ? "Active" : "Blocked"} · ${row.total_shows} shows`,
        status: row.visible ? "active" : "blocked",
        token: token(row),
        actions: [row.visible ? "block" : "unblock"],
        matches: [],
        history: [],
        notice: comic
            ? "Blocking hides this comedian from public surfaces. Unblocking restores visibility; it does not validate identity or remove an ingestion deny-list entry."
            : "Blocking hides this club from public surfaces. Its operating status and scraping source settings are managed separately.",
        evidence: [
            {
                id: "profile",
                title: comic ? "Comedian profile" : "Club profile",
                url: row.website,
                source: row.name,
                kind: "Current record",
                context: comic
                    ? `${row.parent_comedian_id ? `Alias of comedian ID ${row.parent_comedian_id}.` : "Canonical profile."} ${row.block_reason ? `Last block reason: ${row.block_reason}` : "No block reason recorded."}`
                    : `${row.address ?? "Address unavailable"} · ${row.status} · ${row.club_type}${row.closed_at ? ` · Closed ${row.closed_at}` : ""}`,
            },
        ],
    };
}
export async function listVisibilityReviews(
    workflow: VisibilityWorkflow,
    status: string,
    q: string,
    page: number,
): Promise<ReviewPage> {
    const c = config(workflow);
    const where = Prisma.sql`WHERE (${status}='all' OR c.visible=${status === "active"}) AND position(lower(${q}) in lower(c.name))>0`;
    const [rows, counts] = await Promise.all([
        db.$queryRaw<
            Pick<Snapshot, "id" | "name" | "visible" | "total_shows">[]
        >(
            Prisma.sql`SELECT c.id,c.name,c.visible,c.total_shows FROM ${c.table} c ${where} ORDER BY c.name,c.id LIMIT 30 OFFSET ${(page - 1) * 30}`,
        ),
        db.$queryRaw<{ total: number }[]>(
            Prisma.sql`SELECT count(*)::int AS total FROM ${c.table} c ${where}`,
        ),
    ]);
    return {
        items: rows.map((r) => ({
            id: String(r.id),
            workflow,
            title: r.name,
            subtitle: `ID ${r.id} · ${r.visible ? "Active" : "Blocked"} · ${r.total_shows} shows`,
            status: r.visible ? "active" : "blocked",
            evidence: [],
            matches: [],
            history: [],
            token: "",
        })),
        total: counts[0].total,
        page,
    };
}
export async function getVisibilityReview(
    workflow: VisibilityWorkflow,
    id: string,
): Promise<ReviewItem | null> {
    const row = await snapshot(db, workflow, idNumber(id));
    if (!row) return null;
    const result = item(row, workflow),
        c = config(workflow);
    const history = await db.$queryRaw<
        {
            id: number;
            action: string;
            reason: string | null;
            actor_profile_id: string | null;
            created_at: Date;
        }[]
    >`
        SELECT id,action,reason,actor_profile_id,created_at FROM admin_action_audits WHERE entity_type=${c.entity} AND entity_id=${id} ORDER BY id DESC LIMIT 100`;
    result.history = history.map((h) => ({
        id: String(h.id),
        action: h.action.endsWith(".visibility.block")
            ? "Blocked"
            : h.action.endsWith(".visibility.unblock")
              ? "Unblocked"
              : h.action.replaceAll(".", " ").replaceAll("_", " "),
        reason: h.reason ?? "No note recorded",
        actor: h.actor_profile_id ?? "Unknown admin",
        createdAt: new Date(h.created_at).toISOString(),
        undone: false,
    }));
    if (workflow === "comedian_visibility") {
        const denied = await db.$queryRaw<
            { name: string }[]
        >`SELECT name FROM comedian_deny_list WHERE lower(btrim(name))=lower(btrim(${row.name}))`;
        result.evidence.push({
            id: "ingestion",
            title: "Ingestion status",
            source: "Name deny list",
            kind: "Separate ingestion control",
            url: null,
            context: denied.length
                ? "This name is also on the ingestion deny list. Unblocking visibility does not remove that entry."
                : "No matching name deny-list entry.",
        });
    }
    return result;
}
export async function decideVisibilityReview(
    input: ReviewSubmission & { workflow: VisibilityWorkflow },
    actor: string,
): Promise<ReviewResult> {
    const id = idNumber(input.id),
        c = config(input.workflow);
    return db.$transaction(async (tx) => {
        // Lock the entity before checking the snapshot. Including the audit revision
        // also detects a block/unblock cycle that returns visibility to its old value.
        await tx.$queryRaw(
            Prisma.sql`SELECT id FROM ${c.table} WHERE id=${id} FOR UPDATE`,
        );
        const before = await snapshot(tx, input.workflow, id);
        if (!before || token(before) !== input.token)
            throw new ReviewConflict(
                "This item changed. Refresh it before deciding.",
            );
        if (input.action !== (before.visible ? "block" : "unblock"))
            throw new ReviewConflict(
                "This action does not match the current visibility.",
            );
        const visible = input.action === "unblock";
        if (input.workflow === "comedian_visibility" && !visible)
            await tx.$queryRaw`UPDATE comedians SET visible=false,block_reason=${input.reason},block_added_by=${actor},block_added_at=now() WHERE id=${id} RETURNING id`;
        else
            await tx.$queryRaw(
                Prisma.sql`UPDATE ${c.table} SET visible=${visible} WHERE id=${id} RETURNING id`,
            );
        const after = await snapshot(tx, input.workflow, id);
        await tx.$queryRaw`INSERT INTO admin_action_audits(actor_profile_id,action,entity_type,entity_id,reason,before_json,after_json)
            VALUES(${actor},${`${c.entity}.visibility.${input.action}`},${c.entity},${String(id)},${input.reason},${JSON.stringify(before)}::jsonb,${JSON.stringify(after)}::jsonb) RETURNING id`;
        return {
            notice: `${before.name}: ${visible ? "unblocked" : "blocked"}.`,
            revalidateTags: [
                before.name,
                `${c.entity}-detail-data`,
                `${c.entity}-metadata`,
                ...(c.entity === "comedian" ? ["comedian-search-data"] : []),
            ],
        };
    });
}
