/* eslint-disable @typescript-eslint/no-explicit-any */
"use server";
import { QueryHelper } from "../objects/class/query/QueryHelper";
import EntityCarousel from "../components/carousel";
import ShowSearchForm from "../components/form/forms/showSearch";
import { getDB } from "../database";
const { database } = getDB();

export default async function HomePage(props: any) {
    const filters = await QueryHelper.storePageParams(props.searchParams);
    const { comedians } = await database.page.getHomePageData(filters);
    const comediansString = JSON.stringify(comedians);

    return (
        <main>
            <section className="max-w-7xl mx-auto p-18">
                <h2 className="font-bold text-5xl text-white p-5">
                    Laughtrack
                </h2>
                <h3 className="text-white pt-1 p-5 text-xl">Find some funny</h3>
            </section>

            <section>
                <ShowSearchForm />
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
