import { db } from "@/lib/db";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { buildClubImageUrl } from "@/util/imageUtil";
import { Prisma } from "@prisma/client";
import { ClubsResponse } from "./interface";

export async function findClubsWithCount(
    queryHelper: QueryHelper,
): Promise<ClubsResponse> {
    // Common where clause for both count and find
    const whereClause: Prisma.ClubWhereInput = {
        visible: true,
        ...queryHelper.getClubNameClause(),
        ...queryHelper.getClubFiltersClause(),
    };

    const totalCount = await db.club.count({
        where: whereClause,
    });

    // Execute both queries in parallel
    const filteredClubs = await db.club.findMany({
        where: whereClause,
        select: {
            id: true,
            name: true,
            address: true,
            website: true,
            zipCode: true,
        },
        ...queryHelper.getGenericClauses(totalCount),
    });

    return {
        clubs: filteredClubs.map((club) => ({
            id: club.id,
            name: club.name,
            address: club.address,
            zipCode: club.zipCode,
            imageUrl: buildClubImageUrl(club.name),
        })),
        totalCount,
    };
}
