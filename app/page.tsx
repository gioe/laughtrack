"use server";

import { ComedianInterface } from "../interfaces/comedian.interface";
import { getDB } from "../database";
import { EntityType } from "../util/enum";
import EntityCarousel from "../components/custom/carousel/EntityCarousel";
import LandingPageSearchBar from "../components/custom/filters/LandingPageSearchBar";

const {db} = getDB();

interface LandingPageResponseInterface {
    trendingComedians: ComedianInterface[];
    cities: string[];
}

async function getLandingPageData(): Promise<LandingPageResponseInterface> {
    const cities = db.clubs.getAllCities();
    const trendingComedians = db.comedians.getTrendingComedians();

    return Promise.all([cities, trendingComedians]).then((responses) => {
        return {
            cities: responses[0],
            trendingComedians: responses[1],
        };
    });
}

export default async function LandingPage() {
    const { cities, trendingComedians } = await getLandingPageData();

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
                <LandingPageSearchBar cities={cities} />
            </section>

            <section
                className="flex flex-col mx-auto max-w-7xl 
      mt-10 p-6 rounded-lg mb-4 bg-white"
            >
                <EntityCarousel
                    entities={trendingComedians}
                    type={EntityType.Comedian}
                />
            </section>
        </main>
    );
}
