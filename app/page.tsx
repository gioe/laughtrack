"use server";

import EntityCarousel from "../components/carousel";
import ShowSearchForm from "../components/form/forms/showSearch";
import { getDB } from "../database";
import { Comedian } from "../objects/class/comedian/Comedian";
import { FormSelectable } from "../objects/interface";
const { db } = getDB();

const TRENDING_COUNT = 5;

interface LandingPageResponseInterface {
    cities: FormSelectable[];
    trendingComedians: Comedian[];
}

async function getLandingPageData(): Promise<LandingPageResponseInterface> {
    const cities = db.cities.getAll();
    const trendingComedians = db.comedians.getTrendingComedians(TRENDING_COUNT);

    return Promise.all([cities, trendingComedians]).then((responses) => {
        return {
            cities: responses[0],
            trendingComedians: responses[1],
        };
    });
}

export default async function LandingPage() {
    const { cities, trendingComedians } = await getLandingPageData();
    const citiesString = JSON.stringify(cities);

    return (
        <main>
            <section className="max-w-7xl mx-auto p-18">
                <h2 className="font-bold text-5xl text-white p-5">
                    Laughtrack
                </h2>
                <h3 className="text-white pt-1 p-5 text-xl">
                    Find your next show
                </h3>
            </section>

            <section className="m-4 mt-0 -mb-14 px-2 lg:px-4">
                <ShowSearchForm citiesString={citiesString} />
            </section>

            <section
                className="flex flex-col mx-auto max-w-7xl
      mt-10 p-6 rounded-lg mb-4 bg-white"
            >
                <EntityCarousel
                    entityString={JSON.stringify(trendingComedians)}
                />
            </section>
        </main>
    );
}
