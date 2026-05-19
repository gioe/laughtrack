import { db } from "@/lib/db";

type DenyListRow = {
    name: string;
    reason: string;
    added_by: string;
    deleted_at: Date | string;
};

export type AdminComedianListItem = {
    id: number;
    uuid: string;
    name: string;
    popularity: number;
    totalShows: number;
    parent: {
        id: number;
        name: string;
    } | null;
    childCount: number;
    isBlocked: boolean;
    blockReason: string | null;
    blockAddedBy: string | null;
    blockAddedAt: string | null;
};

export type AdminComedianListResult = {
    comedians: AdminComedianListItem[];
    denyListCount: number;
};

function serializeDate(value: Date | string | null | undefined) {
    if (!value) return null;
    return value instanceof Date
        ? value.toISOString()
        : new Date(value).toISOString();
}

function normalizeDenyListName(name: string) {
    return name.trim().toLowerCase();
}

export async function listAdminComedians(): Promise<AdminComedianListResult> {
    const [comedians, denyListRows] = await Promise.all([
        db.comedian.findMany({
            select: {
                id: true,
                uuid: true,
                name: true,
                popularity: true,
                totalShows: true,
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
            orderBy: [{ name: "asc" }, { id: "asc" }],
        }),
        db.$queryRaw<DenyListRow[]>`
            SELECT name, reason, added_by, deleted_at
            FROM comedian_deny_list
        `,
    ]);

    const denyListByName = new Map(
        denyListRows.map((row) => [normalizeDenyListName(row.name), row]),
    );

    return {
        comedians: comedians.map((comedian) => {
            const denyListEntry = denyListByName.get(
                normalizeDenyListName(comedian.name),
            );
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
        }),
        denyListCount: denyListRows.length,
    };
}
