import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import {
    AVAILABLE_SHOW_WHERE,
    PUBLIC_SHOW_SELECT,
    getLineupItemPopularity,
    mapShowRowToDTO,
} from "@/lib/data/show/showSelect";
import { ComedianLineupDTO } from "@/objects/class/comedian/comedianLineup.interface";
import { ShowDTO } from "@/objects/class/show/show.interface";

interface HomeShowQueryOptions {
    zipCode?: string;
    sortByHomeRelevance?: boolean;
}

const HOME_RELEVANCE_CANDIDATE_TAKE = 50;

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
    if (skip > 0 && options.sortByHomeRelevance) {
        throw new Error(
            "findShowsForHome: skip>0 is incompatible with sortByHomeRelevance=true. " +
                "Pagination over a re-sorted candidate window would produce overlapping or missing rows between pages.",
        );
    }
    const queryTake = options.sortByHomeRelevance
        ? Math.max(take, HOME_RELEVANCE_CANDIDATE_TAKE)
        : take;
    const shows = await db.show.findMany({
        where: { AND: [where, AVAILABLE_SHOW_WHERE] },
        select: PUBLIC_SHOW_SELECT,
        orderBy,
        take: queryTake,
        skip,
    });

    const mapped = shows.map((show) => {
        // Home derives imageUrl from the best lineup photo, maps room null →
        // undefined, and only computes distanceMiles when a zip is supplied
        // (search, by contrast, always computes it). See mapShowRowToDTO.
        const dto = mapShowRowToDTO(show, {
            zipCode: options.zipCode,
            imageSource: "lineup",
            room: "coalesce",
            distanceWhenNoZip: "undefined",
        });

        return {
            dto,
            showPopularity: show.popularity,
            lineupPopularity: getLineupPopularity(dto.lineup ?? []),
        };
    });

    if (options.sortByHomeRelevance) {
        mapped.sort((a, b) => compareHomeShowRelevance(a, b));
    }

    return mapped.slice(0, take).map((show) => show.dto);
}

function getLineupPopularity(lineup: ComedianLineupDTO[]): number {
    return lineup.reduce(
        (score, comedian) => score + getLineupItemPopularity(comedian),
        0,
    );
}

function compareHomeShowRelevance(
    a: { dto: ShowDTO; showPopularity: number; lineupPopularity: number },
    b: { dto: ShowDTO; showPopularity: number; lineupPopularity: number },
): number {
    if (a.showPopularity !== b.showPopularity) {
        return b.showPopularity - a.showPopularity;
    }

    if (a.lineupPopularity !== b.lineupPopularity) {
        return b.lineupPopularity - a.lineupPopularity;
    }

    const aDistance = a.dto.distanceMiles ?? Number.POSITIVE_INFINITY;
    const bDistance = b.dto.distanceMiles ?? Number.POSITIVE_INFINITY;
    if (aDistance !== bDistance) return aDistance - bDistance;

    const dateDelta = a.dto.date.getTime() - b.dto.date.getTime();
    if (dateDelta !== 0) return dateDelta;

    return a.dto.id - b.dto.id;
}
