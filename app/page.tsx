"use server";

import { APIRoutePath } from "../objects/enum";
import { HomePageDataResponse } from "./api/home/interface";
import { makeRequest } from "../util/actions/makeRequest";
import { auth } from "../auth";
import HeroComponent from "@/ui/pages/home/hero";
import TrendingComedianGrid from "@/ui/pages/home/comedians";
import TrendingClubsCarousel from "@/ui/pages/home/clubs";
import FooterComponent from "@/ui/pages/home/footer";
import { unstable_cache } from "next/cache";
import { Session } from "next-auth";
import { CACHE } from "@/util/constants/cacheConstants";

export default async function HomePage() {
    const session = await auth();

    const getCachedHomePageData = (currentSession: Session | null) =>
        unstable_cache(
            async () => {
                return makeRequest<HomePageDataResponse>(APIRoutePath.Home, {
                    session: currentSession,
                    revalidate: CACHE.home,
                });
            },
            ["home-page-data", currentSession?.user?.id || ""],
            { revalidate: 86400 },
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
