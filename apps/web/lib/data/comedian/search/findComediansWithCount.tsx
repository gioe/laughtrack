import { db } from "@/lib/db";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import {
    containsAliasTag,
    getEffectiveComedian,
} from "@/util/comedian/comedianUtil";
import { buildComedianImageUrl } from "@/util/imageUtil";
import { Prisma } from "@prisma/client";
import { ComediansResponse } from "./interface";

const COMEDIAN_SELECT = {
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
    taggedComedians: {
        select: {
            tag: true,
        },
    },
    lineupItems: {
        where: {
            show: {
                date: {
                    gt: new Date(),
                },
            },
        },
    },
} as const;

export async function findComediansWithCount(
    helper: QueryHelper,
): Promise<ComediansResponse> {
    try {
        const whereClause: Prisma.ComedianWhereInput = {
            ...helper.getComedianNameClause(),
            ...helper.getComedianFiltersClause(),
            parentComedian: {
                is: null,
            },
        };

        // Get total count first
        const totalCount = await db.comedian.count({ where: whereClause });

        // Then get filtered comedians with pagination
        const filteredComedians = await db.comedian.findMany({
            where: whereClause,
            select: {
                ...COMEDIAN_SELECT,
                ...(helper.getProfileId()
                    ? {
                          favoriteComedians: {
                              where: {
                                  profileId: helper.getProfileId(),
                              },
                              select: {
                                  id: true,
                              },
                          },
                      }
                    : {}),
            },
            ...helper.getGenericClauses(totalCount),
        });

        return {
            comedians: filteredComedians.map((comedian) => {
                const effectiveComedian = getEffectiveComedian(comedian);
                const isAlias = containsAliasTag(
                    effectiveComedian.taggedComedians ?? [],
                );

                return {
                    id: effectiveComedian.id,
                    name: effectiveComedian.name,
                    imageUrl: buildComedianImageUrl(effectiveComedian.name),
                    isAlias,
                    uuid: effectiveComedian.uuid,
                    isFavorite: Boolean(comedian.favoriteComedians?.length),
                    social_data: {
                        id: effectiveComedian.id,
                        linktree: effectiveComedian.linktree,
                        instagram_account: effectiveComedian.instagramAccount,
                        instagram_followers:
                            effectiveComedian.instagramFollowers,
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
    } catch (error) {
        console.error("Error in findComediansWithCount:", error);
        throw new Error("Failed to fetch comedians");
    }
}
