import { db } from "@/lib/db";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { buildComedianImageUrl } from "@/util/imageUtil";
import { Prisma } from "@prisma/client";

export async function getTrendingComedians(userId?: string): Promise<ComedianDTO[]> {
    const comedians = await db.comedian.findMany({
        where: {
            parentComedianId: null,
            name: {
                                contains: "Seaton",
                                mode: Prisma.QueryMode.insensitive,
                            },

            OR: [
                {
                    lineupItems: {
                        some: {
                            show: { date: { gt: new Date().toISOString() } },
                        },
                    },
                },
                {
                    alternativeNames: {
                        some: {
                            lineupItems: {
                                some: {
                                    show: { date: { gt: new Date().toISOString() } },
                                },
                            },
                        },
                    },
                },
            ],
            NOT: {
                taggedComedians: {
                    some: {
                        tag: {
                            value: { in: ["alias", "non_human", "non comic"] }
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
            _count: {
                select: { lineupItems: true }
            },
            alternativeNames: {
                select: {
                    uuid: true,
                    name: true,
                    _count: {
                        select: {
                            lineupItems: true
                        }
                    }
                }
            },
            ...(userId ? {
                favoriteComedians: {
                    where: { userId: Number(userId) },
                },
            } : {}),
        },
    });

    console.log(comedians[0].alternativeNames)
    const topEight = comedians
        .filter(comedian => {
            const alternativeShowCount = comedian.alternativeNames.reduce((sum, alt) =>
                sum + alt._count.lineupItems, 0);
            return (comedian._count.lineupItems + alternativeShowCount) > 3;
        })
        .sort(() => Math.random() - 0.5)
        .slice(0, 8)

    console.log(topEight)

    return topEight
        .map(comedian => ({
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
            show_count: comedian._count.lineupItems +
                comedian.alternativeNames.reduce((sum, alt) =>
                    sum + alt._count.lineupItems, 0),
        }));
}
