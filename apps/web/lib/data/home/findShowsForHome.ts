import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import { ComedianLineupDTO } from "@/objects/class/comedian/comedianLineup.interface";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { buildClubImageUrl } from "@/util/imageUtil";
import { mapTickets } from "@/util/ticket/ticketUtil";
import { filterAndMapLineupItems } from "@/util/comedian/comedianUtil";
import { computeDistanceMiles } from "@/util/distanceUtil";
import { computeShowSoldOut } from "@/util/show/soldOutUtil";

interface HomeShowQueryOptions {
    zipCode?: string;
    sortByHomeRelevance?: boolean;
}

const HOME_RELEVANCE_CANDIDATE_TAKE = 50;

const HOME_SHOW_SELECT = {
    id: true,
    name: true,
    date: true,
    room: true,
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
            city: true,
            state: true,
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
            role: true,
            comedian: {
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
    options: HomeShowQueryOptions = {},
    skip = 0,
): Promise<ShowDTO[]> {
    const queryTake = options.sortByHomeRelevance
        ? Math.max(take, HOME_RELEVANCE_CANDIDATE_TAKE)
        : take;
    const shows = await db.show.findMany({
        where,
        select: HOME_SHOW_SELECT,
        orderBy,
        take: queryTake,
        skip,
    });

    const mapped = shows.map((show) => {
        const lineup = filterAndMapLineupItems(show.lineupItems);
        const distanceMiles = options.zipCode
            ? computeDistanceMiles(options.zipCode, show.club.zipCode)
            : undefined;

        return {
            dto: {
                id: show.id,
                name: show.name,
                date: show.date,
                clubID: show.club.id,
                clubName: show.club.name,
                clubCity: show.club.city,
                clubState: show.club.state,
                address: show.club.address,
                imageUrl:
                    getBestLineupImageUrl(lineup) ??
                    buildClubImageUrl(show.club.name, show.club.hasImage),
                soldOut: computeShowSoldOut(show.name, show.tickets),
                lineup,
                tickets: mapTickets(show.tickets),
                room: show.room ?? undefined,
                distanceMiles,
                timezone: show.club.timezone,
            },
            lineupPopularity: getLineupPopularity(lineup),
        };
    });

    if (options.sortByHomeRelevance) {
        mapped.sort((a, b) => compareHomeShowRelevance(a, b));
    }

    return mapped.slice(0, take).map((show) => show.dto);
}

function getBestLineupImageUrl(lineup: ComedianLineupDTO[]): string | null {
    let best: ComedianLineupDTO | null = null;
    for (const comedian of lineup) {
        if (!comedian.imageUrl) continue;
        if (
            !best ||
            getLineupItemPopularity(comedian) > getLineupItemPopularity(best)
        ) {
            best = comedian;
        }
    }
    return best?.imageUrl ?? null;
}

function getLineupPopularity(lineup: ComedianLineupDTO[]): number {
    return lineup.reduce(
        (score, comedian) => score + getLineupItemPopularity(comedian),
        0,
    );
}

function getLineupItemPopularity(comedian: ComedianLineupDTO): number {
    return comedian.show_count ?? 0;
}

function compareHomeShowRelevance(
    a: { dto: ShowDTO; lineupPopularity: number },
    b: { dto: ShowDTO; lineupPopularity: number },
): number {
    const aDistance = a.dto.distanceMiles ?? Number.POSITIVE_INFINITY;
    const bDistance = b.dto.distanceMiles ?? Number.POSITIVE_INFINITY;
    if (aDistance !== bDistance) return aDistance - bDistance;

    if (a.lineupPopularity !== b.lineupPopularity) {
        return b.lineupPopularity - a.lineupPopularity;
    }

    const dateDelta = a.dto.date.getTime() - b.dto.date.getTime();
    if (dateDelta !== 0) return dateDelta;

    return a.dto.id - b.dto.id;
}
