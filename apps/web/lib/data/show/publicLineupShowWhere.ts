import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";

async function fetchDeniedComedianNames(): Promise<string[]> {
    const rows = await db.$queryRaw<{ name: string }[]>(
        Prisma.sql`SELECT name FROM "comedian_deny_list"`,
    );
    return rows.map((row) => row.name);
}

export async function buildPublicLineupShowWhere(): Promise<Prisma.ShowWhereInput> {
    const deniedNames = await fetchDeniedComedianNames();
    const publicComedianWhere: Prisma.ComedianWhereInput = {
        visible: true,
        taggedComedians: {
            none: {
                tag: {
                    userFacing: false,
                },
            },
        },
        ...(deniedNames.length > 0 ? { name: { notIn: deniedNames } } : {}),
    };

    return {
        OR: [
            { lineupItems: { none: {} } },
            {
                lineupItems: {
                    some: {
                        comedian: publicComedianWhere,
                    },
                },
            },
        ],
    };
}
