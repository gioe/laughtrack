"use server";

import { APIRoutePath } from "../objects/enum";
import { HomePageDataResponse } from "./api/home/interface";
import { makeRequest } from "../util/actions/makeRequest";
import { auth } from "../auth";
import { unstable_cache } from "next/cache";
import { Session } from "next-auth";
import { CACHE } from "@/util/constants/cacheConstants";
import HeroComponent from "@/ui/pages/home/hero";
import TrendingComedianGrid from "@/ui/pages/home/comedians";
import TrendingClubsCarousel from "@/ui/pages/home/clubs";
import FooterComponent from "@/ui/pages/home/footer";

export default async function HomePage() {
    const session = await auth();

    const getCachedHomePageData = (currentSession: Session | null) =>
        unstable_cache(
            async () => {
                try {
                    return await makeRequest<HomePageDataResponse>(
                        APIRoutePath.Home,
                        {
                            session: currentSession,
                            revalidate: CACHE.home,
                        },
                    );
                } catch (error) {
                    console.error("Home page data fetch error:", error);
                    throw error;
                }
            },
            ["home-page-data", currentSession?.user?.id || ""],
            {
                revalidate: CACHE.home,
                tags: ["home-page-data", currentSession?.user?.id || ""],
            },
        );

    const { comedians, clubs } = await getCachedHomePageData(session)();

    return (
        <main className="min-h-screen w-full bg-ivory">
            <HeroComponent user={session?.user} />
            <TrendingComedianGrid comedians={comedians} />
            <TrendingClubsCarousel clubs={clubs} />
            <FooterComponent />
        </main>
    );
}
