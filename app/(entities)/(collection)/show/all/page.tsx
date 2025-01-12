/* eslint-disable @typescript-eslint/no-explicit-any */
"use server";

import { SearchParamsHelper } from "../../../../../objects/class/params/SearchParamsHelper";
import { APIRoutePath } from "../../../../../objects/enum";
import { ShowSearchResponse } from "./interface";
import TableFilterBar from "../../../../../components/filter";
import ShowCard from "../../../../../components/cards/show";
import { Show } from "../../../../../objects/class/show/Show";
import { makeRequest } from "../../../../../util/actions/makeRequest";
import Navbar from "@/components/navbar";
import { auth } from "@/auth";
import DetailHeader from "@/components/search/detailHeader";
import FilterBar from "@/components/search/filterBar";
import ShowTable from "@/components/search/showTable";
export default async function ShowSearchPage(props: any) {
    const session = await auth();

    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );

    const { data, filters } = await makeRequest<ShowSearchResponse>(
        APIRoutePath.ShowSearch,
        {
            searchParams: paramsWrapper.asUrlSearchParams(),
        },
    );

    return (
        <main className="min-h-screen w-full bg-ivory">
            <Navbar currentUser={session?.user} />
            <DetailHeader
                title={`Search shows in ${paramsWrapper.getParamValue("city")}`}
                subTitle={`${data.total} results`}
            />
            <FilterBar />
            <ShowTable shows={JSON.stringify(data.entities)} />
        </main>
    );
}
