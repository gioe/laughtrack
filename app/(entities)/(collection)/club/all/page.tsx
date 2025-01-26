/* eslint-disable @typescript-eslint/no-explicit-any */
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { APIRoutePath, StyleContextKey } from "@/objects/enum";
import { ClubSearchResponse } from "@/app/api/club/search/interface";
import { CACHE } from "@/util/constants/cacheConstants";
import { makeRequest } from "@/util/actions/makeRequest";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { FilterDTO } from "@/objects/interface/filter.interface";
import { Filter } from "@/objects/class/filter/Filter";
import { auth } from "@/auth";
import ClubSearchBar from "@/ui/components/searchbar/club";
import FilterModal from "@/ui/components/modals/filter";
import FilterBar from "@/ui/pages/search/filterBar";
import FooterComponent from "@/ui/pages/home/footer";
import Navbar from "@/ui/components/navbar";
import ClubGrid from "@/ui/components/grid/club";
import SearchDetailHeader from "@/ui/pages/search/detailHeader";

export default async function ClubSearchPage(props: any) {
    const session = await auth();

    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );

    const { data, total, filters } = await makeRequest<ClubSearchResponse>(
        APIRoutePath.ClubSearch,
        {
            searchParams: paramsWrapper.asUrlSearchParams(),
            revalidate: CACHE.search,
        },
    );

    const parsedFilters = filters.map(
        (dto: FilterDTO) =>
            new Filter(dto, paramsWrapper.getParamValue("filters")),
    );

    return (
        <main className="min-h-screen w-full bg-ivory">
            <FilterModal filters={filters} total={total} />
            <StyleContextProvider initialContext={StyleContextKey.Search}>
                <Navbar currentUser={session?.user} />
            </StyleContextProvider>

            <SearchDetailHeader
                title={`Search clubs`}
                subTitle={`${total} results`}
            />
            <FilterBar total={total} filters={parsedFilters.length > 0}>
                <ClubSearchBar />
            </FilterBar>
            <ClubGrid clubs={data} />
            <FooterComponent />
        </main>
    );
}
