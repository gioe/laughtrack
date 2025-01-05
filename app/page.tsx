"use server";
import { unstable_cache } from "next/cache";
import TrendingComedianCarousel from "../components/carousel/comedians";
import TrendingClubsCarousel from "../components/carousel/clubs";
import ShowSearchForm from "../components/form/showSearch";
import { getDB } from "../database";
import { auth } from "../auth";
const { database } = getDB();

const getPageData = unstable_cache(
    async (userId?: string) => {
        return await database.page.getHomePageData(userId);
    },
    ["homePage"],
    { revalidate: 1, tags: ["homePage"] },
);

export default async function HomePage() {
    const session = await auth();
    const { response } = await getPageData(session?.user.id);

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
                <ShowSearchForm cities={JSON.stringify(response.cities)} />
            </section>
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
