import { db } from "@/lib/db";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { buildComedianImageUrl } from "@/util/imageUtil";

const EXCLUSIVITY_TAGS = ["Not A Real Comic"];

export async function findComedians(params: any): Promise<ComedianDTO[]> {
    const {
        query,
        filtersEmpty,
        filters,
        sortBy,
        direction,
        size,
        offset,
        userId,
    } = params;

    console.log(params);

    const filteredComedians = await db.comedian.findMany({
        where: {
            name: {
                contains: query,
                mode: "insensitive",
            },
            ...(!filtersEmpty
                ? {
                      taggedComedians: {
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
            NOT: {
                taggedComedians: {
                    some: {
                        tag: {
                            display: {
                                in: EXCLUSIVITY_TAGS,
                            },
                        },
                    },
                },
            },
        },
        select: {
            id: true,
            uuid: true,
            name: true,
            linktree: true,
            instagramAccount: true,
            instagramFollowers: true,
            tiktokAccount: true,
            tiktokFollowers: true,
            youtubeAccount: true,
            youtubeFollowers: true,
            website: true,
            popularity: true,
            favoriteComedians: {
                select: {
                    id: true,
                },
                ...(userId
                    ? {
                          where: {
                              userId: Number(userId),
                          },
                      }
                    : {}),
            },
            lineupItems: {
                select: {
                    id: true,
                },
                where: {
                    show: {
                        date: {
                            gt: new Date(),
                        },
                    },
                },
            },
        },
        orderBy: {
            [sortBy]: direction,
        },
        take: Number(size),
        skip: offset,
    });

    return filteredComedians.map((comedian) => {
        return {
            id: comedian.id,
            name: comedian.name,
            imageUrl: buildComedianImageUrl(comedian.name),
            isFavorite: comedian.favoriteComedians.length > 0,
            uuid: comedian.uuid,
            social_data: {
                id: comedian.id,
                linktree: comedian.linktree,
                instagram_account: comedian.instagramAccount,
                instagram_followers: comedian.instagramFollowers,
                tiktok_account: comedian.tiktokAccount,
                tiktok_followers: comedian.tiktokFollowers,
                youtube_account: comedian.youtubeAccount,
                youtube_followers: comedian.youtubeFollowers,
                website: comedian.website,
                popularity: comedian.popularity,
            },
            show_count: comedian.lineupItems.length,
        };
    });
}
