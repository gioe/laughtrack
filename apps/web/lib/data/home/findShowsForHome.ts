import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { buildClubImageUrl } from "@/util/imageUtil";
import { mapTickets } from "@/util/ticket/ticketUtil";
import { filterAndMapLineupItems } from "@/util/comedian/comedianUtil";

const HOME_SHOW_SELECT = {
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
} satisfies Prisma.ShowSelect;

/**
 * Shared query + mapper for home-page show sections.
 * Callers are responsible for including `club: { visible: true }` in `where`.
 */
export async function findShowsForHome(
    where: Prisma.ShowWhereInput,
    orderBy:
        | Prisma.ShowOrderByWithRelationInput
        | Prisma.ShowOrderByWithRelationInput[],
    take = 8,
): Promise<ShowDTO[]> {
    const shows = await db.show.findMany({
        where,
        select: HOME_SHOW_SELECT,
        orderBy,
        take,
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
