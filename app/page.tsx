"use server";

import TrendingComedianCarousel from "../components/carousel/comedians";
import TrendingClubsCarousel from "../components/carousel/clubs";
import ShowSearchForm from "../components/form/showSearch";
import { APIRoutePath } from "../objects/enum";
import { HomePageDataResponse } from "./home/interface";
import { makeRequest } from "../util/actions/makeRequest";
import HeroSection from "@/components/hero";
import { auth } from "../auth";

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

    return (
        <main className="min-h-screen w-full">
            <HeroSection user={user} />
            <section className="bg-ivory px-4">
                <h3 className="font-bebas font-semibold text-copper pb-3 text-2xl">
                    Trending
                </h3>
                <div>
                    <TrendingComedianCarousel comedians={response.comedians} />
                </div>
            </section>
            <section className="bg-ivory px-4">
                <h3 className="font-bebas font-semibold text-copper pb-1 text-2xl">
                    Popular Clubs
                </h3>
                <div>
                    <TrendingClubsCarousel clubs={response.clubs} />
                </div>
            </section>
        </main>
    );
}
