import { db } from "@/lib/db";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { RoomHistoryDTO } from "@/objects/class/comedian/roomHistory.interface";
import { buildClubImageUrl } from "@/util/imageUtil";

export async function findRoomHistoryForComedian(
    helper: QueryHelper,
): Promise<RoomHistoryDTO[]> {
    if (!helper.params.comedian) {
        return [];
    }

    const rows = await db.show.findMany({
        where: {
            date: { lt: new Date() },
            club: { visible: true },
            ...helper.getLineupItemClause(),
        },
        select: {
            id: true,
            date: true,
            club: {
                select: {
                    id: true,
                    name: true,
                    city: true,
                    state: true,
                    hasImage: true,
                },
            },
        },
    });

    const byClub = new Map<number, RoomHistoryDTO>();
    for (const row of rows) {
        const existing = byClub.get(row.club.id);
        if (existing) {
            existing.playCount += 1;
            if (row.date > existing.lastPlayedDate) {
                existing.lastPlayedDate = row.date;
            }
            continue;
        }
        byClub.set(row.club.id, {
            clubId: row.club.id,
            clubName: row.club.name,
            clubCity: row.club.city,
            clubState: row.club.state,
            imageUrl: buildClubImageUrl(row.club.name, row.club.hasImage),
            playCount: 1,
            lastPlayedDate: row.date,
        });
    }

    return Array.from(byClub.values()).sort((a, b) => {
        if (b.playCount !== a.playCount) return b.playCount - a.playCount;
        return b.lastPlayedDate.getTime() - a.lastPlayedDate.getTime();
    });
}
