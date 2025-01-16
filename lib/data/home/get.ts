import { db } from "@/lib/db";

export async function getHomePageData(userId: string | null) {
    const clubCount = await db.club.count()

    const venues = await db.club
        .findMany({
            select: {
                id: true,
                address: true,
                name: true,
                shows: {
                    where: {
                        date: {
                            gte: new Date(),
                            lte: new Date(
                                Date.now() + 30 * 24 * 60 * 60 * 1000,
                            ), // 30 days from now
                        },
                    },
                    select: {
                        lineupItems: {
                            select: {
                                comedianId: true,
                            },
                        },
                    },
                },
            },
            take: 8,
        })
        .then((clubs) =>
            clubs.map((club) => ({
                id: club.id,
                address: club.address,
                name: club.name,
                imageUrl:
                    new URL(
                        `/clubs/${club.name}.png`,
                        `https://${process.env.BUNNYCDN_CDN_HOST}/`,
                    ) ??
                    new URL(
                        `logo.png`,
                        `https://${process.env.BUNNYCDN_CDN_HOST}/`,
                    ),
                active_comedian_count: new Set(
                    club.shows.flatMap((show) =>
                        show.lineupItems.map((item) => item.comedianId),
                    ),
                ).size,
            })),
        );

    // Get active comedians
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
            }
        },
    });

    // Filter after the query for comedians with more than 3 upcoming shows
    const filteredComedians = activeComedians.filter(
        (comedian) => comedian.lineupItems.length > 3,
    );

    // Get cities
    const cities = await db.city.findMany({
        select: {
            id: true,
            name: true,
        },
    });

    // Transform comedian data
    const transformedComedians = filteredComedians
        .sort(() => Math.random() - 0.5)
        .slice(0, 8)
        .map((comedian) => ({
            id: comedian.id,
            uuid: comedian.uuid,
            name: comedian.name,
            imageUrl:
                new URL(
                    `/comedians/${comedian.name}.png`,
                    `https://${process.env.BUNNYCDN_CDN_HOST}/`,
                ) ??
                new URL(
                    `logo.png`,
                    `https://${process.env.BUNNYCDN_CDN_HOST}/`,
                ),
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
        }));

    // Return final response
    return {
        comedians: transformedComedians,
        cities: cities,
        clubs: venues,
    };

}
