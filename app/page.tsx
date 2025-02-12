"use server";

import { auth } from "../auth";
import { unstable_cache } from "next/cache";
import { Session } from "next-auth";
import { CACHE } from "@/util/constants/cacheConstants";
import HeroComponent from "@/ui/pages/home/hero";
import TrendingComedianGrid from "@/ui/pages/home/comedians";
import TrendingClubsCarousel from "@/ui/pages/home/clubs";
import FooterComponent from "@/ui/pages/home/footer";
import { getTrendingComedians } from "@/lib/data/home/getTrendingComedians";
import { getPopularClubs } from "@/lib/data/home/getPopularClubs";
import { Prisma } from "@prisma/client";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { ClubDTO } from "@/objects/class/club/club.interface";

export interface HomePageData {
    comedians: ComedianDTO[];
    clubs: ClubDTO[];
}

async function getHomePageData(userId?: string): Promise<HomePageData> {
    try {
        const [comedians, clubs] = await Promise.all([
            getTrendingComedians(userId),
            getPopularClubs(),
        ]);
        return {
            comedians,
            clubs,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}

export default async function HomePage() {
    const session = await auth();

    const getCachedHomePageData = (currentSession: Session | null) =>
        unstable_cache(
            async () => {
                try {
                    return await getHomePageData(
                        currentSession?.profile?.userId,
                    );
                } catch (error) {
                    console.error("Home page data fetch error:", error);
                    throw error;
                }
            },
            [
                "home-page-data",
                session?.user?.id ? session?.user?.id.toString() : "",
            ],
            {
                revalidate: CACHE.home,
                tags: [
                    "home-page-data",
                    session?.user?.id ? session?.user?.id.toString() : "",
                ],
            },
        );

    const { comedians, clubs } = await getCachedHomePageData(session)();

    return (
        <main className="min-h-screen w-full bg-ivory">
            <HeroComponent profile={session?.profile} />
            <TrendingComedianGrid comedians={comedians} />
            <TrendingClubsCarousel clubs={clubs} />
            <FooterComponent />
        </main>
    );
}
