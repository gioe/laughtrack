import { writeAdminActionAudit } from "@/lib/admin/audit";
import type { AdminComedianListItem } from "@/lib/admin/comedianManagement";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import type { Prisma } from "@prisma/client";
import crypto from "crypto";
import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

type ComedianSnapshot = {
    id: number;
    uuid: string;
    name: string;
    popularity: number;
    totalShows: number;
    parentComedianId: number | null;
    parentComedian: { id: number; name: string } | null;
    _count: { alternativeNames: number };
};

type DenyListRow = {
    name: string;
    reason: string;
    added_by: string;
    deleted_at: Date | string;
};

type ComedianAdminWriter = Pick<
    Prisma.TransactionClient,
    "$queryRaw" | "comedian"
> &
    Parameters<typeof writeAdminActionAudit>[0];

const mutationSchema = z.discriminatedUnion("action", [
    z
        .object({
            action: z.literal("set-parent"),
            comedianId: z.number().int().positive(),
            parentComedianId: z.number().int().positive().nullable(),
            reason: z.string().trim().max(1000).optional(),
        })
        .strict(),
    z
        .object({
            action: z.literal("blocklist-add"),
            comedianId: z.number().int().positive(),
            reason: z.string().trim().min(1).max(1000),
        })
        .strict(),
    z
        .object({
            action: z.literal("blocklist-remove"),
            comedianId: z.number().int().positive(),
            reason: z.string().trim().max(1000).optional(),
        })
        .strict(),
]);

const putSchema = z
    .object({
        comedianId: z.number().int().positive(),
        name: z.string().trim().min(1).max(255),
        reason: z.string().trim().max(1000).optional(),
    })
    .strict();

function serializeDate(value: Date | string | null | undefined) {
    if (!value) return null;
    return value instanceof Date
        ? value.toISOString()
        : new Date(value).toISOString();
}

function normalizeName(name: string) {
    return name.trim().replace(/\s+/g, " ");
}

function generateComedianUuid(name: string) {
    const cleanedName = Array.from(name)
        .filter(
            (char) =>
                /[0-9A-Za-z]/.test(char) ||
                char.toLowerCase() !== char.toUpperCase(),
        )
        .join("");
    return crypto
        .createHash("md5")
        .update(cleanedName.toLowerCase())
        .digest("hex");
}

function snapshotForAudit(comedian: ComedianSnapshot) {
    return {
        id: comedian.id,
        uuid: comedian.uuid,
        name: comedian.name,
        popularity: comedian.popularity,
        totalShows: comedian.totalShows,
        parentComedianId: comedian.parentComedianId,
        parent: comedian.parentComedian,
        childCount: comedian._count.alternativeNames,
    };
}

function serializeComedian(
    comedian: ComedianSnapshot,
    denyListEntry: DenyListRow | null,
): AdminComedianListItem {
    return {
        id: comedian.id,
        uuid: comedian.uuid,
        name: comedian.name,
        popularity: comedian.popularity,
        totalShows: comedian.totalShows,
        parent: comedian.parentComedian,
        childCount: comedian._count.alternativeNames,
        isBlocked: Boolean(denyListEntry),
        blockReason: denyListEntry?.reason ?? null,
        blockAddedBy: denyListEntry?.added_by ?? null,
        blockAddedAt: serializeDate(denyListEntry?.deleted_at),
    };
}

async function readBody(req: NextRequest) {
    try {
        return await req.json();
    } catch {
        return null;
    }
}

async function findComedianSnapshot(
    tx: Pick<Prisma.TransactionClient, "comedian">,
    comedianId: number,
) {
    return tx.comedian.findUnique({
        where: { id: comedianId },
        select: {
            id: true,
            uuid: true,
            name: true,
            popularity: true,
            totalShows: true,
            parentComedianId: true,
            parentComedian: {
                select: {
                    id: true,
                    name: true,
                },
            },
            _count: {
                select: {
                    alternativeNames: true,
                },
            },
        },
    });
}

async function findDenyListEntry(
    tx: Pick<Prisma.TransactionClient, "$queryRaw">,
    name: string,
) {
    const rows = await tx.$queryRaw<DenyListRow[]>`
        SELECT name, reason, added_by, deleted_at
        FROM comedian_deny_list
        WHERE lower(btrim(name)) = lower(btrim(${name}))
        LIMIT 1
    `;
    return rows[0] ?? null;
}

async function createsParentCycle(
    tx: Pick<Prisma.TransactionClient, "comedian">,
    comedianId: number,
    parentComedianId: number,
) {
    let nextParentId: number | null = parentComedianId;
    const seen = new Set<number>();

    while (nextParentId) {
        if (nextParentId === comedianId) return true;
        if (seen.has(nextParentId)) return true;
        seen.add(nextParentId);

        const parent: { parentComedianId: number | null } | null =
            await tx.comedian.findUnique({
                where: { id: nextParentId },
                select: { parentComedianId: true },
            });
        nextParentId = parent?.parentComedianId ?? null;
    }

    return false;
}

function revalidateComedianSurfaces(name: string) {
    revalidateTag("comedian-search-data");
    revalidateTag("comedian-detail-data");
    revalidateTag("comedian-metadata");
    revalidateTag(name);
}

export async function PATCH(req: NextRequest) {
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

    try {
        const result = await db.$transaction(
            async (tx: ComedianAdminWriter) => {
                const before = await findComedianSnapshot(
                    tx,
                    parsed.data.comedianId,
                );
                if (!before)
                    return { error: "Comedian not found", status: 404 };

                if (parsed.data.action === "set-parent") {
                    const parentComedianId = parsed.data.parentComedianId;

                    if (parentComedianId === before.id) {
                        return {
                            error: "A comedian cannot be their own parent",
                            status: 400,
                        };
                    }

                    if (parentComedianId) {
                        const parent = await findComedianSnapshot(
                            tx,
                            parentComedianId,
                        );
                        if (!parent) {
                            return {
                                error: "Parent comedian not found",
                                status: 404,
                            };
                        }
                        if (
                            await createsParentCycle(
                                tx,
                                before.id,
                                parentComedianId,
                            )
                        ) {
                            return {
                                error: "That parent relationship would create a cycle",
                                status: 400,
                            };
                        }
                    }

                    await tx.comedian.update({
                        where: { id: before.id },
                        data: { parentComedianId },
                    });

                    const after = await findComedianSnapshot(tx, before.id);
                    if (!after) {
                        return { error: "Comedian not found", status: 404 };
                    }

                    await writeAdminActionAudit(tx, {
                        actorProfileId: profileId,
                        action: "comedian.parent.update",
                        entityType: "comedian",
                        entityId: before.id,
                        reason: parsed.data.reason?.trim() || null,
                        before: snapshotForAudit(before),
                        after: snapshotForAudit(after),
                    });

                    const denyListEntry = await findDenyListEntry(
                        tx,
                        after.name,
                    );
                    return {
                        comedian: serializeComedian(after, denyListEntry),
                        name: after.name,
                    };
                }

                const beforeDenyListEntry = await findDenyListEntry(
                    tx,
                    before.name,
                );

                if (parsed.data.action === "blocklist-remove") {
                    if (!beforeDenyListEntry) {
                        return {
                            comedian: serializeComedian(before, null),
                            name: before.name,
                        };
                    }

                    const deletedRows = await tx.$queryRaw<DenyListRow[]>`
                        DELETE FROM comedian_deny_list
                        WHERE lower(btrim(name)) = lower(btrim(${before.name}))
                        RETURNING name, reason, added_by, deleted_at
                    `;
                    const deletedEntry = deletedRows[0] ?? beforeDenyListEntry;

                    await writeAdminActionAudit(tx, {
                        actorProfileId: profileId,
                        action: "comedian_deny_list.delete",
                        entityType: "comedian_deny_list",
                        entityId: deletedEntry.name,
                        reason: parsed.data.reason?.trim() || null,
                        before: {
                            name: deletedEntry.name,
                            reason: deletedEntry.reason,
                            addedBy: deletedEntry.added_by,
                            addedAt: serializeDate(deletedEntry.deleted_at),
                        },
                        after: {},
                    });

                    return {
                        comedian: serializeComedian(before, null),
                        name: before.name,
                    };
                }

                const reason = parsed.data.reason.trim();
                const name = normalizeName(before.name);
                const rows = await tx.$queryRaw<DenyListRow[]>`
                INSERT INTO comedian_deny_list (name, reason, added_by)
                VALUES (${beforeDenyListEntry?.name ?? name}, ${reason}, ${profileId})
                ON CONFLICT (name) DO UPDATE
                SET reason = EXCLUDED.reason,
                    added_by = EXCLUDED.added_by,
                    deleted_at = now()
                RETURNING name, reason, added_by, deleted_at
            `;
                const afterDenyListEntry = rows[0];

                await writeAdminActionAudit(tx, {
                    actorProfileId: profileId,
                    action: beforeDenyListEntry
                        ? "comedian_deny_list.update"
                        : "comedian_deny_list.create",
                    entityType: "comedian_deny_list",
                    entityId: afterDenyListEntry.name,
                    reason,
                    before: beforeDenyListEntry
                        ? {
                              name: beforeDenyListEntry.name,
                              reason: beforeDenyListEntry.reason,
                              addedBy: beforeDenyListEntry.added_by,
                              addedAt: serializeDate(
                                  beforeDenyListEntry.deleted_at,
                              ),
                          }
                        : {},
                    after: {
                        name: afterDenyListEntry.name,
                        reason: afterDenyListEntry.reason,
                        addedBy: afterDenyListEntry.added_by,
                        addedAt: serializeDate(afterDenyListEntry.deleted_at),
                    },
                });

                return {
                    comedian: serializeComedian(before, afterDenyListEntry),
                    name: before.name,
                };
            },
        );

        if ("error" in result) {
            return NextResponse.json(
                { error: result.error },
                { status: result.status },
            );
        }

        revalidateComedianSurfaces(result.name);
        return NextResponse.json({ ok: true, comedian: result.comedian });
    } catch (error) {
        console.error("Admin comedians PATCH failed:", error);
        return NextResponse.json({ error: "Update failed" }, { status: 500 });
    }
}

export async function PUT(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const { profileId } = gate.context;

    const parsed = putSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    const name = normalizeName(parsed.data.name);
    const uuid = generateComedianUuid(name);

    try {
        const result = await db.$transaction(
            async (tx: ComedianAdminWriter) => {
                const before = await findComedianSnapshot(
                    tx,
                    parsed.data.comedianId,
                );
                if (!before)
                    return { error: "Comedian not found", status: 404 };

                const conflictingComedian = await tx.comedian.findUnique({
                    where: { uuid },
                    select: { id: true, name: true },
                });
                if (
                    conflictingComedian &&
                    conflictingComedian.id !== before.id
                ) {
                    return {
                        error: `Generated UUID already belongs to ${conflictingComedian.name}`,
                        status: 409,
                    };
                }

                await tx.comedian.update({
                    where: { id: before.id },
                    data: { name, uuid },
                });

                const after = await findComedianSnapshot(tx, before.id);
                if (!after) {
                    return { error: "Comedian not found", status: 404 };
                }

                await writeAdminActionAudit(tx, {
                    actorProfileId: profileId,
                    action: "comedian.update",
                    entityType: "comedian",
                    entityId: before.id,
                    reason: parsed.data.reason?.trim() || null,
                    before: snapshotForAudit(before),
                    after: snapshotForAudit(after),
                });

                const denyListEntry = await findDenyListEntry(tx, after.name);
                return {
                    comedian: serializeComedian(after, denyListEntry),
                    previousName: before.name,
                    name: after.name,
                };
            },
        );

        if ("error" in result) {
            return NextResponse.json(
                { error: result.error },
                { status: result.status },
            );
        }

        revalidateComedianSurfaces(result.previousName);
        revalidateComedianSurfaces(result.name);
        return NextResponse.json({ ok: true, comedian: result.comedian });
    } catch (error) {
        console.error("Admin comedians PUT failed:", error);
        return NextResponse.json({ error: "Update failed" }, { status: 500 });
    }
}
