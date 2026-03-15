import { db } from "@/lib/db";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { buildClubImageUrl } from "@/util/imageUtil";
import { mapTickets } from "@/util/ticket/ticketUtil";
import { filterAndMapLineupItems } from "@/util/comedian/comedianUtil";

const LIMIT = 8;

export async function getShowsTonight(): Promise<ShowDTO[]> {
    const now = new Date();
    const startOfDay = new Date(now);
    startOfDay.setHours(0, 0, 0, 0);
    const endOfDay = new Date(now);
    endOfDay.setHours(23, 59, 59, 999);

    const shows = await db.show.findMany({
        where: {
            date: { gte: startOfDay, lte: endOfDay },
            club: { visible: true },
        },
        select: {
            id: true,
            name: true,
            date: true,
            tickets: {
                select: {
                    price: true,
                    soldOut: true,
                    purchaseUrl: true,
                    type: true,
                },
            },
            club: {
                select: {
                    name: true,
                    address: true,
                },
            },
            lineupItems: {
                where: {
                    comedian: {
                        taggedComedians: {
                            none: { tag: { userFacing: false } },
                        },
                    },
                },
                select: {
                    comedian: {
                        select: {
                            id: true,
                            uuid: true,
                            name: true,
                            parentComedian: {
                                select: {
                                    id: true,
                                    uuid: true,
                                    name: true,
                                    taggedComedians: { select: { tag: true } },
                                },
                            },
                            taggedComedians: { select: { tag: true } },
                        },
                    },
                },
            },
        },
        orderBy: { date: "asc" },
        take: LIMIT,
    });

    return shows.map((show) => ({
        id: show.id,
        name: show.name,
        date: show.date,
        clubName: show.club.name,
        address: show.club.address,
        imageUrl: buildClubImageUrl(show.club.name),
        soldOut:
            show.tickets.length > 0 &&
            show.tickets.every((t) => t.soldOut === true),
        lineup: filterAndMapLineupItems(show.lineupItems),
        tickets: mapTickets(show.tickets),
    }));
}
