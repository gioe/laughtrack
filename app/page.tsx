"use server";
import { unstable_cache } from "next/cache";
import TrendingComedianCarousel from "../components/carousel/comedians";
import TrendingClubsCarousel from "../components/carousel/clubs";
import ShowSearchForm from "../components/form/showSearch";
import { auth } from "../auth";
import { db } from "./lib/db";

async function getHomeData(userId?: string) {
    // Get venues/clubs data
    const venues = await db.club
        .findMany({
            select: {
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

const getPageData = unstable_cache(
    async (userId?: string) => {
        return await getHomeData(userId);
    },
    ["homePage"],
    { revalidate: 1, tags: ["homePage"] },
);

export default async function HomePage() {
    const session = await auth();
    const { comedians, cities, clubs } = await getPageData(session?.user.id);

    return (
        <main className="pt-36">
            <section className="max-w-7xl mx-auto text-center">
                <h2 className="font-fjalla text-5xl text-copper p-5">
                    Laughtrack
                </h2>
                <h3 className="font-fjalla font-semibold text-copper pt-1 p-5 text-xl">
                    Laugh a little
                </h3>
            </section>
            <section className="p-8">
                <ShowSearchForm cities={JSON.stringify(cities)} />
            </section>
            <section className="bg-ivory px-4">
                <h3 className="font-bebas font-semibold text-copper pb-3 text-2xl">
                    Trending
                </h3>
                <div>
                    <TrendingComedianCarousel comedians={comedians} />
                </div>
            </section>
            <section className="bg-ivory px-4">
                <h3 className="font-bebas font-semibold text-copper pb-1 text-2xl">
                    Popular Clubs
                </h3>
                <div>
                    <TrendingClubsCarousel clubs={clubs} />
                </div>
            </section>
        </main>
    );
}
