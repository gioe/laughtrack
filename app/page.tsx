"use server";

import { APIRoutePath } from "../objects/enum";
import { HomePageDataResponse } from "./home/interface";
import { makeRequest } from "../util/actions/makeRequest";
import { auth } from "../auth";
import HeroComponent from "@/components/sections/hero";
import TrendingComedianCarousel from "@/components/sections/comedians";
import TrendingClubsCarousel from "@/components/sections/clubs";
import FooterComponent from "@/components/sections/footer";

export async function getCurrentUser() {
    try {
        const session = await auth();
        if (!session?.user?.email) {
            return null;
        }
        return {
            id: session.user.id,
            email: session.user.email,
            role: session.user.role,
        };
    } catch (error) {
        console.log(error);
        return null;
    }
}

export default async function HomePage() {
    const user = await getCurrentUser();

    const { response } = await makeRequest<HomePageDataResponse>(
        APIRoutePath.Home,
    );
    console.log(response);

    return (
        <main className="min-h-screen w-full bg-ivory">
            <HeroComponent user={user} cities={response.cities} />
            <TrendingComedianCarousel comedians={response.comedians} />
            <TrendingClubsCarousel clubs={response.clubs} />
            <FooterComponent />
        </main>
    );
}
