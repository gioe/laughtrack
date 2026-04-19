import { db } from "@/lib/db";
import { NotFoundError } from "@/objects/NotFoundError";
import { filterAndMapLineupItems } from "@/util/comedian/comedianUtil";
import { buildClubImageUrl } from "@/util/imageUtil";
import { mapTickets } from "@/util/ticket/ticketUtil";
import { Prisma } from "@prisma/client";
import { ShowDetailDTO } from "./interface";

export async function findShowById(id: number): Promise<ShowDetailDTO> {
    try {
        const row = await db.show.findUnique({
            where: { id },
            select: {
                id: true,
                name: true,
                date: true,
                description: true,
                room: true,
                showPageUrl: true,
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
                        id: true,
                        name: true,
                        address: true,
                        hasImage: true,
                        timezone: true,
                        visible: true,
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
                                taggedComedians: { select: { tag: true } },
                            },
                        },
                    },
                },
            },
        });

        if (!row) {
            throw new NotFoundError(`Show with id "${id}" not found`);
        }

        // Hidden clubs stay hidden on the show detail page too — don't leak
        // their shows just because the URL is guessable.
        if (!row.club.visible) {
            throw new NotFoundError(`Show with id "${id}" not found`);
        }

        const clubName = row.club.name;
        return {
            id: row.id,
            name: row.name,
            date: row.date,
            description: row.description ?? undefined,
            room: row.room,
            address: row.club.address,
            clubName,
            imageUrl: buildClubImageUrl(clubName, row.club.hasImage),
            soldOut:
                row.tickets.length > 0 &&
                row.tickets.every((t) => t.soldOut === true),
            lineup: filterAndMapLineupItems(row.lineupItems),
            tickets: mapTickets(row.tickets),
            distanceMiles: null,
            timezone: row.club.timezone,
            showPageUrl: row.showPageUrl,
            clubSlug: encodeURIComponent(clubName),
            isPast: row.date.getTime() < Date.now(),
            clubId: row.club.id,
        };
    } catch (error) {
        if (error instanceof NotFoundError) {
            throw error;
        }
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
