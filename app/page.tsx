"use server";

import { headers } from "next/headers";
import { ParamsWrapper } from "../objects/class/params/ParamsWrapper";
import { URLParams } from "../objects/type/urlParams";
import { QueryHelper } from "../objects/class/query/QueryHelper";
import { HeadersWrapper } from "../objects/class/headers/HeadersWrapper";
import { HomePageData, HomePageDTO } from "./home/interface";
import { homePageDataMapper as mapper } from "./home/mapper";
import EntityCarousel from "../components/carousel";
import ShowSearchForm from "../components/form/forms/showSearch";
import { DirectionParamValue, SortParamValue, URLParam } from "../objects/enum";

export default async function HomePage(props: {
    searchParams: Promise<URLParams>;
}) {
    await HeadersWrapper.updateHeaders(headers());
    await ParamsWrapper.updateWithServerParams(props.searchParams);
    ParamsWrapper.setParamValue(URLParam.Sort, SortParamValue.Date);
    ParamsWrapper.setParamValue(
        URLParam.Direction,
        DirectionParamValue.Ascending,
    );

    const { cities, comedians } = await QueryHelper.getPageData<
        HomePageDTO,
        HomePageData
    >(mapper);

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

            <section className="m-4 mt-0 -mb-14 px-2 lg:px-4">
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
