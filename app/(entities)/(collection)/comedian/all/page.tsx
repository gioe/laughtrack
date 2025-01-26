/* eslint-disable @typescript-eslint/no-explicit-any */
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { APIRoutePath, StyleContextKey } from "@/objects/enum";
import { CACHE } from "@/util/constants/cacheConstants";
import { makeRequest } from "@/util/actions/makeRequest";
import { ComedianSearchResponse } from "@/app/api/comedian/search/interface";
import { auth } from "@/auth";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import FooterComponent from "@/ui/pages/home/footer";
import ComedianGrid from "@/ui/components/grid/comedian";
import SearchDetailHeader from "@/ui/pages/search/detailHeader";
import ComedianSearchBar from "@/ui/components/searchbar/comedian";
import FilterModal from "@/ui/components/modals/filter";
import Navbar from "@/ui/components/navbar";
import FilterBar from "@/ui/pages/search/filterBar";

export default async function ComedianSearchPage(props: any) {
    const session = await auth();

    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );

    const { data, total, filters } = await makeRequest<ComedianSearchResponse>(
        APIRoutePath.ComedianSearch,
        {
            searchParams: paramsWrapper.asUrlSearchParams(),
            revalidate: CACHE.search,
        },
    );

    return (
        <main className="min-h-screen w-full bg-ivory">
            <FilterModal filters={filters} total={total} />
            <StyleContextProvider initialContext={StyleContextKey.Search}>
                <Navbar currentUser={session?.user} />
            </StyleContextProvider>

            <SearchDetailHeader
                title={`Search comedians`}
                subTitle={`${total} results`}
            />

            <FilterBar total={total} filters={filters.length > 0}>
                <ComedianSearchBar />
            </FilterBar>
            <ComedianGrid
                comedians={data}
                className="grid grid-cols-1 m:grid-cols-2 lg:grid-cols-2 xl:grid-cols-5 gap-6"
            />

            <FooterComponent />
        </main>
    );
}
