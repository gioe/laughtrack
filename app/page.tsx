"use server";
import { unstable_cache } from "next/cache";
import TrendingComedianCarousel from "../components/carousel";
import ShowSearchForm from "../components/form/showSearch";
import { getDB } from "../database";
const { database } = getDB();

const getPageData = unstable_cache(
    async () => {
        return await database.page.getHomePageData();
    },
    ["homePage"],
    { revalidate: 1, tags: ["homePage"] },
);

export default async function HomePage() {
    const { response } = await getPageData();

    return (
        <main>
            <section className="max-w-7xl mx-auto p-18 text-center">
                <h2 className="font-sans font-bold text-5xl text-copper p-5">
                    Laughtrack
                </h2>
                <h3 className="font-sans font-semibold text-copper pt-1 p-5 text-l">
                    Get out and laugh a little
                </h3>
            </section>
            <section>
                <ShowSearchForm cities={JSON.stringify(response.cities)} />
            </section>
            <section className="flex flex-col mx-auto max-w-7xl mt-10 p-6 rounded-lg mb-4 bg-white">
                <TrendingComedianCarousel comedians={response.comedians} />
            </section>
        </main>
    );
}
