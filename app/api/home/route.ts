/* eslint-disable @typescript-eslint/no-explicit-any */
import { NextResponse } from "next/server";
import { db } from "../../lib/db";
import { headers } from "next/headers";
import { HomePageDTO } from "../../home/interface";

async function getHomeData(userId: string | null) {
    // Get venues/clubs data
    const venues = await db.club
        .findMany({
            select: {
                id: true,
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
            take: 6,
        })
        .then((clubs) =>
            clubs.map((club) => ({
                id: club.id,
                name: club.name,
                count: new Set(
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
            },
            favoriteComedians: userId
                ? {
                    where: {
                        userId: Number(userId),
                    },
                }
                : false,
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
        .slice(0, 10)
        .map((comedian) => ({
            id: comedian.id,
            uuid: comedian.uuid,
            name: comedian.name,
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
            is_favorite: userId ? comedian.favoriteComedians.length > 0 : false,
            show_count: comedian.lineupItems.length,
        }));

    // Return final response
    return {
        comedians: transformedComedians,
        cities: cities,
        clubs: venues,
    };
}


export async function GET(request: Request) {
    const headersList = await headers();
    const userId = headersList.get("user_id");

    return getHomeData(userId)
        .then((response: HomePageDTO) => NextResponse.json({ response }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
