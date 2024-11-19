"use server";

import { headers } from "next/headers";
import { URLParams } from "../objects/type/urlParams";
import { QueryHelper } from "../objects/class/query/QueryHelper";
import EntityCarousel from "../components/carousel";
import ShowSearchForm from "../components/form/forms/showSearch";
import { getDB } from "../database";
const { database } = getDB();

export default async function HomePage(props: {
    searchParams: Promise<URLParams>;
}) {
    await QueryHelper.storePageParams(props.searchParams, headers());
    const { cities, comedians } = await database.page.getHomePageData();

    const comediansString = JSON.stringify(comedians);
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

            <section className="m-4 mt-0 -mb-8 px-2 lg:px-4">
                <ShowSearchForm cities={citiesString} />
            </section>

            <section
                className="flex flex-col mx-auto max-w-7xl
      mt-10 p-6 rounded-lg mb-4 bg-white"
            >
                <EntityCarousel entities={comediansString} />
            </section>
        </main>
    );
}
