"use server";

import { APIRoutePath } from "../objects/enum";
import { HomePageDataResponse } from "./api/home/interface";
import { makeRequest } from "../util/actions/makeRequest";
import { auth } from "../auth";
import HeroComponent from "@/ui/pages/home/hero";
import TrendingComedianGrid from "@/ui/pages/home/comedians";
import TrendingClubsCarousel from "@/ui/pages/home/clubs";
import FooterComponent from "@/ui/pages/home/footer";

export default async function HomePage() {
    const session = await auth();

    const { response } = await makeRequest<HomePageDataResponse>(
        APIRoutePath.Home,
    );

    return (
        <main className="min-h-screen w-full bg-ivory">
            <HeroComponent user={session?.user} />
            {/* <TrendingComedianGrid comedians={response.comedians} />
            <TrendingClubsCarousel clubs={response.clubs} />
            <FooterComponent /> */}
        </main>
    );
}
