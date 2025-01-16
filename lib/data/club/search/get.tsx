import { ClubSearchDTO } from "@/app/api/club/search/interface";
import { db } from "@/lib/db";

export async function getSearchedClubs(params: any): Promise<ClubSearchDTO> {
    const totalCount = await db.club.count({
        where: {
            name: {
                contains: params.query,
                mode: "insensitive",
            },
            ...(!params.tagsEmpty
                ? {
                      taggedClubs: {
                          some: {
                              tag: {
                                  value: {
                                      in: params.tags,
                                  },
                              },
                          },
                      },
                  }
                : {}),
        },
    });

    // Get filtered data
    const clubs = await db.club.findMany({
        select: {
            id: true,
            name: true,
            address: true,
            website: true,
        },
        where: {
            name: {
                contains: params.query,
                mode: "insensitive",
            },
            ...(!params.tagsEmpty
                ? {
                      taggedClubs: {
                          some: {
                              tag: {
                                  value: {
                                      in: params.tags,
                                  },
                              },
                          },
                      },
                  }
                : {}),
        },
        orderBy: {
            [params.sortBy]: params.direction,
        },
        take: Number(params.size),
        skip: params.offset,
    });

    return {
        response: {
            data: clubs,
            total: totalCount,
        },
    };
}
