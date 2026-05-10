import { db } from "@/lib/db";
import { ComedianLineupDTO } from "@/objects/class/comedian/comedianLineup.interface";
import { filterAndMapLineupItems } from "@/util/comedian/comedianUtil";
import { Prisma } from "@prisma/client";

const DEFAULT_LIMIT = 10;
const MIN_CO_BILL_COUNT = 2;

interface CoBillRow {
    uuid: string;
    co_bill_count: number | bigint;
}

interface FindCoBilledComediansOptions {
    comedianId: number;
    now?: Date;
    limit?: number;
}

export async function findCoBilledComediansForComedian({
    comedianId,
    now = new Date(),
    limit = DEFAULT_LIMIT,
}: FindCoBilledComediansOptions): Promise<ComedianLineupDTO[]> {
    const oneYearAgo = new Date(now);
    oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);

    const rows = await db.$queryRaw<CoBillRow[]>(Prisma.sql`
        WITH target AS (
            SELECT id, uuid
            FROM "comedians"
            WHERE id = ${comedianId}
        ),
        target_shows AS (
            SELECT li."show_id"
            FROM "lineup_items" li
            JOIN "shows" s ON s.id = li."show_id"
            JOIN "clubs" cl ON cl.id = s."club_id"
            JOIN target t ON t.uuid = li."comedian_id"
            WHERE s.date >= ${oneYearAgo}
              AND s.date < ${now}
              AND cl.visible = true
        )
        SELECT li."comedian_id" AS uuid, COUNT(*) AS co_bill_count
        FROM "lineup_items" li
        JOIN target_shows ts ON ts."show_id" = li."show_id"
        JOIN target t ON TRUE
        JOIN "comedians" co_billed ON co_billed.uuid = li."comedian_id"
        WHERE li."comedian_id" <> t.uuid
          AND (
              co_billed."parent_comedian_id" IS NULL
              OR co_billed."parent_comedian_id" <> t.id
          )
          AND NOT EXISTS (
              SELECT 1
              FROM "tagged_comedians" tc
              JOIN "tags" tag ON tag.id = tc."tag_id"
              WHERE tc."comedian_id" = li."comedian_id"
                AND tag."user_facing" = false
          )
        GROUP BY li."comedian_id"
        HAVING COUNT(*) >= ${MIN_CO_BILL_COUNT}
        ORDER BY COUNT(*) DESC, li."comedian_id" ASC
        LIMIT ${limit}
    `);

    if (rows.length === 0) {
        return [];
    }

    const uuids = rows.map((row) => row.uuid);
    const comedians = await db.comedian.findMany({
        where: { uuid: { in: uuids } },
        select: {
            id: true,
            uuid: true,
            name: true,
            hasImage: true,
            _count: {
                select: {
                    lineupItems: true,
                },
            },
            parentComedian: {
                select: {
                    id: true,
                    uuid: true,
                    name: true,
                    hasImage: true,
                    _count: {
                        select: {
                            lineupItems: true,
                        },
                    },
                    taggedComedians: {
                        select: { tag: true },
                    },
                },
            },
            taggedComedians: {
                select: { tag: true },
            },
        },
    });

    const comediansByUuid = new Map(
        comedians.map((comedian) => [comedian.uuid, comedian]),
    );

    const seen = new Set<string>();
    return rows
        .map((row) => comediansByUuid.get(row.uuid))
        .filter((comedian): comedian is NonNullable<typeof comedian> =>
            Boolean(comedian),
        )
        .map((comedian) => filterAndMapLineupItems([{ comedian }])[0])
        .filter((comedian) => comedian.id !== comedianId)
        .filter((comedian) => seen.add(comedian.uuid));
}
