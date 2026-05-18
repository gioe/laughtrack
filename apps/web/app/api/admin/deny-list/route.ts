import { writeAdminActionAudit } from "@/lib/admin/audit";
import { db } from "@/lib/db";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import type { Prisma } from "@prisma/client";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

type DenyListRow = {
    name: string;
    reason: string;
    added_by: string;
    deleted_at: Date | string;
};

const mutationSchema = z.object({
    name: z.string().trim().min(1).max(255),
    reason: z.string().trim().min(1).max(1000),
});

type DenyListWriter = Pick<Prisma.TransactionClient, "$queryRaw"> &
    Parameters<typeof writeAdminActionAudit>[0];

function normalizeName(name: string) {
    return name.trim().replace(/\s+/g, " ");
}

function serializeRow(row: DenyListRow) {
    return {
        name: row.name,
        reason: row.reason,
        addedBy: row.added_by,
        addedAt:
            row.deleted_at instanceof Date
                ? row.deleted_at.toISOString()
                : new Date(row.deleted_at).toISOString(),
    };
}

async function readBody(req: NextRequest) {
    try {
        return await req.json();
    } catch {
        return null;
    }
}

async function findEntry(
    tx: Pick<Prisma.TransactionClient, "$queryRaw">,
    name: string,
) {
    const rows = await tx.$queryRaw<DenyListRow[]>`
        SELECT name, reason, added_by, deleted_at
        FROM comedian_deny_list
        WHERE lower(name) = lower(${name})
        LIMIT 1
    `;
    return rows[0] ?? null;
}

export async function GET(req?: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;

    const query = req?.nextUrl.searchParams.get("q")?.trim() ?? "";
    const rows = query
        ? await db.$queryRaw<DenyListRow[]>`
            SELECT name, reason, added_by, deleted_at
            FROM comedian_deny_list
            WHERE name ILIKE ${`%${query}%`}
               OR reason ILIKE ${`%${query}%`}
               OR added_by ILIKE ${`%${query}%`}
            ORDER BY deleted_at DESC, name ASC
            LIMIT 200
        `
        : await db.$queryRaw<DenyListRow[]>`
            SELECT name, reason, added_by, deleted_at
            FROM comedian_deny_list
            ORDER BY deleted_at DESC, name ASC
            LIMIT 200
        `;

    return NextResponse.json({ entries: rows.map(serializeRow) });
}

export async function POST(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const { profileId } = gate.context;

    const parsed = mutationSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    const name = normalizeName(parsed.data.name);
    const reason = parsed.data.reason.trim();

    try {
        const entry = await db.$transaction(async (tx: DenyListWriter) => {
            const before = await findEntry(tx, name);
            const nameToWrite = before?.name ?? name;
            const rows = await tx.$queryRaw<DenyListRow[]>`
                INSERT INTO comedian_deny_list (name, reason, added_by)
                VALUES (${nameToWrite}, ${reason}, ${profileId})
                ON CONFLICT (name) DO UPDATE
                SET reason = EXCLUDED.reason,
                    added_by = EXCLUDED.added_by,
                    deleted_at = now()
                RETURNING name, reason, added_by, deleted_at
            `;
            const after = serializeRow(rows[0]);

            await writeAdminActionAudit(tx, {
                actorProfileId: profileId,
                action: before
                    ? "comedian_deny_list.update"
                    : "comedian_deny_list.create",
                entityType: "comedian_deny_list",
                entityId: after.name,
                reason,
                before: before ? serializeRow(before) : {},
                after,
            });

            return after;
        });

        return NextResponse.json({ ok: true, entry }, { status: 201 });
    } catch (error) {
        console.error("Admin deny-list POST failed:", error);
        return NextResponse.json({ error: "Create failed" }, { status: 500 });
    }
}

export async function DELETE(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const { profileId } = gate.context;

    const parsed = mutationSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    const name = normalizeName(parsed.data.name);
    const reason = parsed.data.reason.trim();

    try {
        const removed = await db.$transaction(async (tx: DenyListWriter) => {
            const before = await findEntry(tx, name);
            if (!before) return null;

            await tx.$queryRaw<DenyListRow[]>`
                DELETE FROM comedian_deny_list
                WHERE name = ${before.name}
                RETURNING name, reason, added_by, deleted_at
            `;

            await writeAdminActionAudit(tx, {
                actorProfileId: profileId,
                action: "comedian_deny_list.delete",
                entityType: "comedian_deny_list",
                entityId: before.name,
                reason,
                before: serializeRow(before),
                after: {},
            });

            return serializeRow(before);
        });

        if (!removed) {
            return NextResponse.json(
                { error: "Deny-list entry not found" },
                { status: 404 },
            );
        }

        return NextResponse.json({ ok: true, entry: removed });
    } catch (error) {
        console.error("Admin deny-list DELETE failed:", error);
        return NextResponse.json({ error: "Delete failed" }, { status: 500 });
    }
}
