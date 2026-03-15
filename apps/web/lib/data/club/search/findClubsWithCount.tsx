import { db } from "@/lib/db";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
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

export async function findClubsWithCount(
    queryHelper: QueryHelper,
): Promise<ClubsResponse> {
    try {
        // Common where clause for both count and find
        const whereClause: Prisma.ClubWhereInput = {
            visible: true,
            ...queryHelper.getClubNameClause(),
            ...queryHelper.getClubFiltersClause(),
        };

        // Get total count first
        const totalCount = await db.club.count({
            where: whereClause,
        });

        // Then get filtered clubs with pagination
        const filteredClubs = await db.club.findMany({
            where: whereClause,
            select: CLUB_SELECT,
            ...queryHelper.getGenericClauses(totalCount),
        });

        return {
            clubs: filteredClubs.map((club) => ({
                id: club.id,
                name: club.name,
                address: club.address,
                city: club.city ?? undefined,
                state: club.state ?? undefined,
                zipCode: club.zipCode,
                imageUrl: buildClubImageUrl(club.name),
                show_count: club._count.shows,
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
