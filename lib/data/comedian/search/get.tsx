import { ComedianSearchDTO } from "@/app/api/comedian/search/interface";
import { db } from "@/lib/db";

export async function getSearchedComedians(
    params: any,
): Promise<ComedianSearchDTO> {
    // First get total count
    const totalCount = await db.comedian.count({
        where: {
            name: {
                contains: params.query,
                mode: "insensitive",
            },
            ...(!params.tagsEmpty
                ? {
                      taggedComedians: {
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

    // Then get filtered data
    const comedians = await db.comedian.findMany({
        select: {
            id: true,
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
        },
        where: {
            name: {
                contains: params.query,
                mode: "insensitive",
            },
            ...(!params.tagsEmpty
                ? {
                      taggedComedians: {
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

    // Transform the data to match the original SQL output structure
    const formattedData = comedians.map((comedian) => ({
        id: comedian.id,
        name: comedian.name,
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
    }));

    return {
        response: {
            data: formattedData,
            total: totalCount,
        },
    };
}
