import { db } from "@/lib/db";
import { ClubDTO } from "@/objects/class/club/club.interface";
import { buildClubImageUrl } from "@/util/imageUtil";
import { Prisma } from "@prisma/client";

interface ClubsResponse {
    clubs: ClubDTO[];
    totalCount: number;
}

export async function findClubsWithCount(params: any): Promise<ClubsResponse> {
    const { club, filters, filtersEmpty, sortBy, direction, size, offset } =
        params;

    // Common where clause for both count and find
    const whereClause: Prisma.ClubWhereInput = {
        visible: true,
        name: {
            contains: club,
            mode: Prisma.QueryMode.insensitive,
        },
        ...(!filtersEmpty
            ? {
                  taggedClubs: {
                      some: {
                          tag: {
                              display: {
                                  in: filters,
                              },
                          },
                      },
                  },
              }
            : {}),
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
            orderBy: {
                [sortBy]: direction,
            },
            take: Number(size),
            skip: offset,
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
