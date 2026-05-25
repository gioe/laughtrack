import { db } from "@/lib/db";
import { QueryHelper, CLUB_SORT_MAP } from "@/objects/class/query/QueryHelper";
import { computeDistanceMiles } from "@/util/distanceUtil";
import { buildClubImageUrl } from "@/util/imageUtil";
import { Prisma } from "@prisma/client";
import { ClubsResponse } from "./interface";

const CLUB_SELECT = {
    id: true,
    name: true,
    address: true,
    city: true,
    state: true,
    website: true,
    zipCode: true,
    hasImage: true,
    chainId: true,
    chain: {
        select: {
            name: true,
            slug: true,
        },
    },
} as const;

// Built fresh per request to avoid capturing a stale module-load Date
function buildClubSelect() {
    return {
        ...CLUB_SELECT,
        _count: {
            select: {
                shows: {
                    where: {
                        date: {
                            gt: new Date(),
                        },
                    },
                },
            },
        },
    } as const;
}

interface ChainedClub {
    id: number;
    chainId: number | null;
    name: string;
    upcomingShows: number;
}

/**
 * Pick one "flagship" club per chain to represent it in the default club-search
 * grid (collapsing a multi-location chain to a single card). The flagship is the
 * location with the most upcoming shows, tie-broken alphabetically by name.
 * Returns the flagship ids and, keyed by flagship id, that chain's location count.
 */
export function selectChainFlagships(clubs: ChainedClub[]): {
    flagshipIds: number[];
    locationCountByFlagship: Map<number, number>;
} {
    const flagshipByChain = new Map<
        number,
        {
            id: number;
            name: string;
            upcomingShows: number;
            locationCount: number;
        }
    >();

    for (const club of clubs) {
        if (club.chainId == null) continue;
        const current = flagshipByChain.get(club.chainId);
        if (!current) {
            flagshipByChain.set(club.chainId, {
                id: club.id,
                name: club.name,
                upcomingShows: club.upcomingShows,
                locationCount: 1,
            });
            continue;
        }
        current.locationCount += 1;
        const isMoreActive =
            club.upcomingShows > current.upcomingShows ||
            (club.upcomingShows === current.upcomingShows &&
                club.name.localeCompare(current.name) < 0);
        if (isMoreActive) {
            current.id = club.id;
            current.name = club.name;
            current.upcomingShows = club.upcomingShows;
        }
    }

    const flagshipIds: number[] = [];
    const locationCountByFlagship = new Map<number, number>();
    for (const entry of flagshipByChain.values()) {
        flagshipIds.push(entry.id);
        locationCountByFlagship.set(entry.id, entry.locationCount);
    }
    return { flagshipIds, locationCountByFlagship };
}

export async function findClubsWithCount(
    queryHelper: QueryHelper,
): Promise<ClubsResponse> {
    try {
        const now = new Date();
        const includeEmpty = queryHelper.params.includeEmpty === "true";
        // Collapse multi-location chains to one flagship card in the default
        // browse. Skipped when a specific chain is selected, so all of that
        // chain's locations remain visible.
        const dedupeChains = !queryHelper.params.chain;

        // Base filters shared by the count, the page query, and (when deduping)
        // the flagship lookup — so the flagship is chosen among matching clubs.
        const baseWhere: Prisma.ClubWhereInput = {
            visible: true,
            status: "active",
            clubType: { not: "festival" },
            ...queryHelper.getClubNameClause(),
            ...queryHelper.getClubFiltersClause(),
            ...queryHelper.getChainClause(),
            ...(!includeEmpty && {
                shows: { some: { date: { gt: now } } },
            }),
        };

        const chainLocationCountByFlagship = new Map<number, number>();
        let whereClause: Prisma.ClubWhereInput = baseWhere;

        if (dedupeChains) {
            const chainedClubs = await db.club.findMany({
                where: { AND: [baseWhere, { chainId: { not: null } }] },
                select: {
                    id: true,
                    chainId: true,
                    name: true,
                    _count: {
                        select: { shows: { where: { date: { gt: now } } } },
                    },
                },
            });

            const { flagshipIds, locationCountByFlagship } =
                selectChainFlagships(
                    chainedClubs.map((club) => ({
                        id: club.id,
                        chainId: club.chainId,
                        name: club.name,
                        upcomingShows: club._count.shows,
                    })),
                );
            for (const [id, count] of locationCountByFlagship) {
                chainLocationCountByFlagship.set(id, count);
            }

            // Keep standalone clubs (no chain) plus one flagship per chain.
            whereClause = {
                AND: [
                    baseWhere,
                    { OR: [{ chainId: null }, { id: { in: flagshipIds } }] },
                ],
            };
        }

        // Get total count first
        const totalCount = await db.club.count({
            where: whereClause,
        });

        // Then get filtered clubs with pagination
        const { orderBy, take, skip } = queryHelper.getGenericClauses(
            totalCount,
            CLUB_SORT_MAP,
        );
        // Inject totalShows tiebreaker after the primary sort so more-active clubs
        // surface first among ties — skip when already sorting by totalShows to
        // avoid a duplicate orderBy entry.
        const primaryField = Object.keys(orderBy[0])[0];
        const clubOrderBy =
            primaryField === "totalShows"
                ? orderBy
                : [
                      orderBy[0],
                      { totalShows: "desc" as const },
                      ...orderBy.slice(1),
                  ];
        const filteredClubs = await db.club.findMany({
            where: whereClause,
            select: buildClubSelect(),
            orderBy: clubOrderBy,
            take,
            skip,
        });

        const searchedZip = queryHelper.params.zip;
        return {
            clubs: filteredClubs.map((club) => ({
                id: club.id,
                name: club.name,
                address: club.address,
                city: club.city ?? undefined,
                state: club.state ?? undefined,
                zipCode: club.zipCode,
                imageUrl: buildClubImageUrl(club.name, club.hasImage),
                showCount: club._count.shows,
                distanceMiles: computeDistanceMiles(searchedZip, club.zipCode),
                chainId: club.chainId ?? null,
                chainName: club.chain?.name ?? null,
                chainSlug: club.chain?.slug ?? null,
                chainLocationCount:
                    chainLocationCountByFlagship.get(club.id) ?? null,
            })),
            totalCount,
        };
    } catch (error) {
        if (error instanceof Error) {
            console.error("Error in findClubsWithCount:", error);
            throw error;
        }
        throw new Error("An unknown error occurred while fetching clubs");
    }
}
