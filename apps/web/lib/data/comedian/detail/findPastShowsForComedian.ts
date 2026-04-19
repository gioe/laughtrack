import { db } from "@/lib/db";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { filterAndMapLineupItems } from "@/util/comedian/comedianUtil";
import { buildClubImageUrl } from "@/util/imageUtil";
import { mapTickets } from "@/util/ticket/ticketUtil";
import { Prisma } from "@prisma/client";

export const PAST_SHOWS_PAGE_SIZE = 20;

export interface PastShowsResult {
    shows: ShowDTO[];
    totalCount: number;
}

export interface PastShowsOptions {
    /** 0-indexed page number. Defaults to 0 (first page). */
    page?: number;
    /** Page size. Defaults to PAST_SHOWS_PAGE_SIZE. */
    size?: number;
}

export async function findPastShowsForComedian(
    helper: QueryHelper,
    options: PastShowsOptions = {},
): Promise<PastShowsResult> {
    if (!helper.params.comedian) {
        return { shows: [], totalCount: 0 };
    }

    const page = Math.max(0, options.page ?? 0);
    const size = Math.max(1, options.size ?? PAST_SHOWS_PAGE_SIZE);

    const whereClause: Prisma.ShowWhereInput = {
        date: { lt: new Date() },
        club: { visible: true },
        ...helper.getLineupItemClause(),
    };

    const [totalCount, rows] = await Promise.all([
        db.show.count({ where: whereClause }),
        db.show.findMany({
            where: whereClause,
            select: {
                id: true,
                name: true,
                date: true,
                description: true,
                room: true,
                popularity: true,
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
                        zipCode: true,
                        hasImage: true,
                        timezone: true,
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
                                hasImage: true,
                                parentComedian: {
                                    select: {
                                        id: true,
                                        uuid: true,
                                        name: true,
                                        hasImage: true,
                                        taggedComedians: {
                                            select: { tag: true },
                                        },
                                    },
                                },
                                taggedComedians: {
                                    select: { tag: true },
                                },
                            },
                        },
                    },
                },
            },
            orderBy: [{ date: "desc" }, { id: "desc" }],
            skip: page * size,
            take: size,
        }),
    ]);

    return {
        totalCount,
        shows: rows.map((show) => ({
            id: show.id,
            date: show.date,
            name: show.name,
            description: show.description ?? undefined,
            room: show.room,
            address: show.club.address,
            clubName: show.club.name,
            imageUrl: buildClubImageUrl(show.club.name, show.club.hasImage),
            soldOut:
                show.tickets.length > 0 &&
                show.tickets.every((t) => t.soldOut === true),
            lineup: filterAndMapLineupItems(
                show.lineupItems,
                helper.getUserId(),
            ),
            tickets: mapTickets(show.tickets),
            distanceMiles: null,
            timezone: show.club.timezone,
        })),
    };
}
