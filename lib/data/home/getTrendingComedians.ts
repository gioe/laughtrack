import { db } from "@/lib/db";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { combineComedianResults } from "@/util/comedian/comedian_util";
import { buildComedianImageUrl } from "@/util/imageUtil";

export async function getTrendingComedians(userId?: string): Promise<ComedianDTO[]> {
    const activeComedians = await db.comedian.findMany({
        where: {
            lineupItems: {
                some: {
                    show: {
                        date: {
                            gt: new Date(),
                        },
                    },
                },
            },
            NOT: {
                taggedComedians: {
                    some: {
                        tag: {
                            value: "alias",
                        },
                    },
                },
            },
        },
        select: {
            id: true,
            uuid: true,
            name: true,
            instagramAccount: true,
            instagramFollowers: true,
            tiktokAccount: true,
            tiktokFollowers: true,
            youtubeAccount: true,
            youtubeFollowers: true,
            website: true,
            popularity: true,
            linktree: true,
            parentComedian: {
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
            alternativeNames: {
                select: {
                    id: true,
                    name: true,
                },
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
            ...(userId ? {
                favoriteComedians: {
                    where: {
                        userId: Number(userId),
                    },
                },
            } : {}),
        },
    });

    console.log(activeComedians)
    const combinedComedians = combineComedianResults(activeComedians)


    // Filter after the query for comedians with more than 3 upcoming shows
    const filteredComedians = combinedComedians.filter(
        (comedian) => comedian.lineupItems.length > 3,
    );


    // Transform comedian data
    return filteredComedians
        .sort(() => Math.random() - 0.5)
        .slice(0, 8)
        .map((comedian) => {
            return {
                id: comedian.id,
                uuid: comedian.uuid,
                name: comedian.name,
                isFavorite:
                    comedian.favoriteComedians == undefined
                        ? false
                        : comedian.favoriteComedians.length > 0,
                imageUrl: buildComedianImageUrl(comedian.name),
                social_data: {
                    id: comedian.id,
                    instagram_account: comedian.instagramAccount,
                    instagram_followers: comedian.instagramFollowers,
                    tiktok_account: comedian.tiktokAccount,
                    tiktok_followers: comedian.tiktokFollowers,
                    youtube_account: comedian.youtubeAccount,
                    youtube_followers: comedian.youtubeFollowers,
                    website: comedian.website,
                    popularity: comedian.popularity,
                    linktree: comedian.linktree,
                },
                show_count: comedian.lineupItems.length,
            }
        });
}
