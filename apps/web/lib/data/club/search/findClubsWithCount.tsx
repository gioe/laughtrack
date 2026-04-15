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

export async function findClubsWithCount(
    queryHelper: QueryHelper,
): Promise<ClubsResponse> {
    try {
        // Common where clause for both count and find
        const includeEmpty = queryHelper.params.includeEmpty === "true";
        const whereClause: Prisma.ClubWhereInput = {
            visible: true,
            status: "active",
            ...queryHelper.getClubNameClause(),
            ...queryHelper.getClubFiltersClause(),
            ...queryHelper.getChainClause(),
            ...(!includeEmpty && {
                shows: { some: { date: { gt: new Date() } } },
            }),
        };

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
                show_count: club._count.shows,
                distanceMiles: computeDistanceMiles(searchedZip, club.zipCode),
                chainId: club.chainId ?? null,
                chainName: club.chain?.name ?? null,
                chainSlug: club.chain?.slug ?? null,
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
