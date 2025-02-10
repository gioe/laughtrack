/* eslint-disable @typescript-eslint/no-explicit-any */
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { APIRoutePath, QueryProperty, StyleContextKey } from "@/objects/enum";
import { CACHE } from "@/util/constants/cacheConstants";
import { makeRequest } from "@/util/actions/makeRequest";
import { ComedianSearchResponse } from "@/app/api/comedian/search/interface";
import { auth } from "@/auth";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import FooterComponent from "@/ui/pages/home/footer";
import ComedianGrid from "@/ui/components/grid/comedian";
import SearchDetailHeader from "@/ui/pages/search/header";
import FilterModal from "@/ui/components/modals/filter";
import Navbar from "@/ui/components/navbar";
import FilterBar from "@/ui/pages/search/filterBar";
import { FilterDTO } from "@/objects/interface/filter.interface";
import { Filter } from "@/objects/class/filter/Filter";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { ParamsProvider } from "@/contexts/ParamsProvider";

export default async function ComedianSearchPage(props: any) {
    const session = await auth();

    const paramsHelper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );

    const { data, total, filters } = await makeRequest<ComedianSearchResponse>(
        APIRoutePath.ComedianSearch,
        {
            searchParams: paramsHelper.asUrlSearchParams(),
            session,
            next: {
                revalidate: CACHE.search,
                tags: ["comedian-search-data", session?.user?.id || ""],
            },
        },
    );
    const parsedFilters = filters.map(
        (dto: FilterDTO) =>
            new Filter(dto, paramsHelper.getParamValue(QueryProperty.Filters)),
    );

    return (
        <main className="min-h-screen w-full bg-ivory">
            <Navbar currentUser={session?.user} />

            <ParamsProvider value={paramsHelper.asUrlSearchParams()}>
                <FilterModal filters={filters} total={total} />

                <SearchDetailHeader
                    title={`Search comedians`}
                    subTitle={`${total} results`}
                />

                <FilterBar
                    variant={SearchVariant.AllComedians}
                    total={total}
                    filters={filters.length > 0}
                />

                <ComedianGrid
                    comedians={data}
                    className="grid grid-cols-1 m:grid-cols-2 lg:grid-cols-2 xl:grid-cols-5 gap-6"
                />
            </ParamsProvider>

            <FooterComponent />
        </main>
    );
}
