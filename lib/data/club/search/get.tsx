import { ClubSearchDTO } from "@/app/api/club/search/interface";
import { db } from "@/lib/db";

const buildClubImageUrl = (clubName: string) => {
    return (
        new URL(
            `/clubs/${clubName}.png`,
            `https://${process.env.BUNNYCDN_CDN_HOST}/`,
        ) ?? new URL(`logo.png`, `https://${process.env.BUNNYCDN_CDN_HOST}/`)
    );
};

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
    const clubData = await db.club.findMany({
        select: {
            id: true,
            name: true,
            address: true,
            website: true,
            zipCode: true,
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

    const clubs = clubData.map((club) => {
        return {
            id: club.id,
            name: club.name,
            address: club.address,
            zipCode: club.zipCode,
            imageUrl: buildClubImageUrl(club.name),
        };
    });

    return {
        response: {
            data: clubs,
            total: totalCount,
        },
    };
}
