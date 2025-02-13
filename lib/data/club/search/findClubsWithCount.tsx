import { db } from "@/lib/db";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { buildClubImageUrl } from "@/util/imageUtil";
import { Prisma } from "@prisma/client";

interface ClubsResponse {
    clubs: ClubDTO[];
    totalCount: number;
}

export async function findClubsWithCount(
    queryHelper: QueryHelper,
): Promise<ClubsResponse> {
    // Common where clause for both count and find
    const whereClause: Prisma.ClubWhereInput = {
        visible: true,
        ...queryHelper.getClubNameClause(),
        ...queryHelper.getClubFiltersClause(),
    };

    // Execute both queries in parallel
    const [filteredClubs, totalCount] = await Promise.all([
        db.club.findMany({
            where: whereClause,
            select: {
                id: true,
                name: true,
                address: true,
                website: true,
                zipCode: true,
            },
            ...queryHelper.getGenericClauses(),
        }),
        db.club.count({
            where: whereClause,
        }),
    ]);

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
