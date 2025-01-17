/* eslint-disable @typescript-eslint/no-explicit-any */
"use server";

import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { APIRoutePath, StyleContextKey } from "@/objects/enum";
import { makeRequest } from "@/util/actions/makeRequest";
import { auth } from "@/auth";
import { ShowSearchResponse } from "@/app/api/show/search/interface";
import Navbar from "@/ui/components/navbar";
import FilterBar from "@/ui/pages/search/filterBar";
import ShowTable from "@/ui/pages/search/table";
import FooterComponent from "@/ui/pages/home/footer";
import SearchDetailHeader from "@/ui/pages/search/detailHeader";
import { StyleContextProvider } from "@/contexts/StyleProvider";

export default async function ShowSearchPage(props: any) {
    const session = await auth();

    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );

    const { data } = await makeRequest<ShowSearchResponse>(
        APIRoutePath.ShowSearch,
        {
            searchParams: paramsWrapper.asUrlSearchParams(),
        },
    );
    return (
        <main className="min-h-screen w-full bg-ivory">
            <Navbar currentUser={session?.user} />

            <SearchDetailHeader
                title={`Search shows in ${paramsWrapper.getParamValue("city")}`}
                subTitle={`${data.total} results`}
            />
            <FilterBar />
            <ShowTable shows={JSON.stringify(data.entities)} />
            <FooterComponent />
        </main>
    );
}
