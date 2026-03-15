import zipcodes from "zipcodes";
import { db } from "@/lib/db";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { buildClubImageUrl } from "@/util/imageUtil";
import { mapTickets } from "@/util/ticket/ticketUtil";
import { filterAndMapLineupItems } from "@/util/comedian/comedianUtil";

const LIMIT = 8;

function resolveZipCodes(zipCode: string, radius?: number): string[] {
    if (!radius || radius < 1 || radius > 500) return [zipCode];
    try {
        const results = zipcodes.radius(zipCode, radius);
        if (!results || results.length === 0) return [zipCode];
        return results.map((z: string | zipcodes.ZipCode) =>
            typeof z === "string" ? z : z.zip,
        );
    } catch {
        return [zipCode];
    }
}

export async function getShowsNearZip(
    zipCode: string,
    radius?: number,
): Promise<ShowDTO[]> {
    if (!zipCode || !/^\d{5}(-\d{4})?$/.test(zipCode)) return [];

    const now = new Date();
    const nearbyZips = resolveZipCodes(zipCode, radius);

    const shows = await db.show.findMany({
        where: {
            date: { gte: now },
            club: {
                visible: true,
                zipCode: { in: nearbyZips },
            },
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
