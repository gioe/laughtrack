import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { RoomHistoryDTO } from "@/objects/class/comedian/roomHistory.interface";
import { buildClubImageUrl } from "@/util/imageUtil";
import { resolveCanonicalComedianIdentityByName } from "./resolveCanonicalComedianIdentity";

interface RoomHistoryRow {
    club_id: number;
    club_name: string;
    club_city: string | null;
    club_state: string | null;
    has_image: boolean;
    play_count: number | bigint;
    last_played_date: Date;
}

export async function findRoomHistoryForComedian(
    helper: QueryHelper,
): Promise<RoomHistoryDTO[]> {
    const comedian = helper.params.comedian;
    if (!comedian) {
        return [];
    }

    const identity = await resolveCanonicalComedianIdentityByName(comedian);
    if (!identity) {
        return [];
    }

    const now = new Date();

    const rows = await db.$queryRaw<RoomHistoryRow[]>(Prisma.sql`
        SELECT
            cl.id AS club_id,
            cl.name AS club_name,
            cl.city AS club_city,
            cl.state AS club_state,
            cl."has_image" AS has_image,
            COUNT(DISTINCT s.id) AS play_count,
            MAX(s.date) AS last_played_date
        FROM "shows" s
        JOIN "clubs" cl ON cl.id = s."club_id"
        JOIN "lineup_items" li ON li."show_id" = s.id
        WHERE s.date < ${now}
          AND cl.visible = true
          AND li."comedian_id" IN (${Prisma.join(identity.memberUuids)})
        GROUP BY cl.id, cl.name, cl.city, cl.state, cl."has_image"
        ORDER BY play_count DESC, last_played_date DESC
    `);

    return rows.map((row) => ({
        clubId: row.club_id,
        clubName: row.club_name,
        clubCity: row.club_city,
        clubState: row.club_state,
        imageUrl: buildClubImageUrl(row.club_name, row.has_image),
        playCount: Number(row.play_count),
        lastPlayedDate: new Date(row.last_played_date),
    }));
}
