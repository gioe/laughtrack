import { db } from "@/lib/db";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { buildComedianImageUrl } from "@/util/imageUtil";
import { Prisma } from "@prisma/client";

const EXCLUSIVITY_TAGS = ["Not A Real Comic"];

interface ComediansResponse {
    comedians: ComedianDTO[];
    totalCount: number;
}

export async function findComediansWithCount(
    params: any,
): Promise<ComediansResponse> {
    const {
        sortBy,
        comedian,
        offset,
        size,
        direction,
        filtersEmpty,
        filters,
        userId,
    } = params;

    // Common where clause for both count and find
    const whereClause: Prisma.ComedianWhereInput = {
        name: {
            contains: comedian,
            mode: Prisma.QueryMode.insensitive,
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
    };

    // Execute both queries in parallel
    const [filteredComedians, totalCount] = await Promise.all([
        db.comedian.findMany({
            where: whereClause,
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
                ...(userId
                    ? {
                          favoriteComedians: {
                              where: {
                                  userId: Number(userId),
                              },
                          },
                      }
                    : {}),
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
        }),
        db.comedian.count({
            where: whereClause,
        }),
    ]);

    return {
        comedians: filteredComedians.map((comedian) => ({
            id: comedian.id,
            name: comedian.name,
            imageUrl: buildComedianImageUrl(comedian.name),
            uuid: comedian.uuid,
            isFavorite:
                comedian.favoriteComedians == undefined
                    ? false
                    : comedian.favoriteComedians.length > 0,
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
        })),
        totalCount,
    };
}
