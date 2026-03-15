import { db } from "@/lib/db";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import {
    containsAliasTag,
    getEffectiveComedian,
} from "@/util/comedian/comedianUtil";
import { buildComedianImageUrl } from "@/util/imageUtil";
import { SortParamValue } from "@/objects/enum/sortParamValue";
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
    _count: {
        select: {
            lineupItems: {
                where: {
                    show: {
                        date: {
                            gt: new Date(),
                        },
                    },
                },
            },
        },
    },
} as const;

function mapComedian(
    comedian: Prisma.ComedianGetPayload<{
        select: typeof COMEDIAN_SELECT & {
            favoriteComedians?: { select: { id: true } };
        };
    }>,
) {
    const effectiveComedian = getEffectiveComedian(comedian);
    const isAlias = containsAliasTag(effectiveComedian.taggedComedians ?? []);

    return {
        id: effectiveComedian.id,
        name: effectiveComedian.name,
        imageUrl: buildComedianImageUrl(effectiveComedian.name),
        isAlias,
        uuid: effectiveComedian.uuid,
        isFavorite: Boolean(
            (comedian as { favoriteComedians?: { id: number }[] })
                .favoriteComedians?.length,
        ),
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
        show_count: comedian._count.lineupItems,
    };
}

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

        const favoriteSelect = helper.getProfileId()
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
            : {};

        // Get total count first
        const totalCount = await db.comedian.count({ where: whereClause });

        // For show_count_desc: fetch all matching comedians, sort in JS, paginate in JS.
        // The _count.lineupItems subquery is computed in SQL (not N+1).
        if (helper.params.sort === SortParamValue.ShowCountDesc) {
            const allComedians = await db.comedian.findMany({
                where: whereClause,
                select: {
                    ...COMEDIAN_SELECT,
                    ...favoriteSelect,
                },
            });

            allComedians.sort(
                (a, b) => b._count.lineupItems - a._count.lineupItems,
            );

            const { take, skip } = helper.getGenericClauses(totalCount);
            const paginated = allComedians.slice(skip, skip + take);

            return {
                comedians: paginated.map(mapComedian),
                totalCount,
            };
        }

        const filteredComedians = await db.comedian.findMany({
            where: whereClause,
            select: {
                ...COMEDIAN_SELECT,
                ...favoriteSelect,
            },
            ...helper.getGenericClauses(totalCount),
        });

        return {
            comedians: filteredComedians.map(mapComedian),
            totalCount,
        };
    } catch (error) {
        console.error("Error in findComediansWithCount:", error);
        throw new Error("Failed to fetch comedians");
    }
}
