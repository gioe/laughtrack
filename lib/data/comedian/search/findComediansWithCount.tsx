import { db } from "@/lib/db";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { getEffectiveComedian } from "@/util/comedian/comedianUtil";
import { buildComedianImageUrl } from "@/util/imageUtil";
import { Prisma } from "@prisma/client";

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

    // Where clause remains the same...
    const whereClause: Prisma.ComedianWhereInput = {
        name: {
            contains: comedian,
            mode: Prisma.QueryMode.insensitive,
        },
        parentComedian: null,
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
                        userFacing: false,
                    },
                },
            },
        },
    };

    // Execute both queries in parallel with updated select
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
                alternativeNames: {
                    select: {
                        id: true,
                        name: true,
                        uuid: true,
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
                },
                ...(userId
                    ? {
                          favoriteComedians: {
                              where: {
                                  user: {
                                      userId,
                                  },
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
        comedians: filteredComedians.map((comedian) => {
            // If this comedian has a parent, use the parent's data
            const effectiveComedian = getEffectiveComedian(comedian);

            return {
                id: effectiveComedian.id,
                name: effectiveComedian.name,
                imageUrl: buildComedianImageUrl(effectiveComedian.name),
                uuid: effectiveComedian.uuid,
                isFavorite:
                    comedian.favoriteComedians == undefined
                        ? false
                        : comedian.favoriteComedians.length > 0,
                social_data: {
                    id: effectiveComedian.id,
                    linktree: effectiveComedian.linktree,
                    instagram_account: effectiveComedian.instagramAccount,
                    instagram_followers: effectiveComedian.instagramFollowers,
                    tiktok_account: effectiveComedian.tiktokAccount,
                    tiktok_followers: effectiveComedian.tiktokFollowers,
                    youtube_account: effectiveComedian.youtubeAccount,
                    youtube_followers: effectiveComedian.youtubeFollowers,
                    website: effectiveComedian.website,
                    popularity: effectiveComedian.popularity,
                },
                show_count: comedian.lineupItems.length,
            };
        }),
        totalCount,
    };
}
