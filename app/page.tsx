"use server";

import { APIRoutePath } from "../objects/enum";
import { HomePageDataResponse } from "./home/interface";
import { makeRequest } from "../util/actions/makeRequest";
import { auth } from "../auth";
import HeroComponent from "@/components/home/hero";
import TrendingComedianCarousel from "@/components/home/comedians";
import TrendingClubsCarousel from "@/components/home/clubs";
import FooterComponent from "@/components/home/footer";

export default async function HomePage() {
    const session = await auth();

    const { response } = await makeRequest<HomePageDataResponse>(
        APIRoutePath.Home,
    );

    return (
        <main className="min-h-screen w-full bg-ivory">
            <HeroComponent
                user={session?.user}
                cities={JSON.stringify(response.cities)}
            />
            <TrendingComedianCarousel comedians={response.comedians} />
            <TrendingClubsCarousel clubs={response.clubs} />
            <FooterComponent />
        </main>
    );
}
