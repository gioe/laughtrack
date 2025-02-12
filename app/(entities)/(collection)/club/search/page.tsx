/* eslint-disable @typescript-eslint/no-explicit-any */
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import {
    APIRoutePath,
    EntityType,
    QueryProperty,
    StyleContextKey,
} from "@/objects/enum";
import { ClubSearchResponse } from "@/app/api/club/search/interface";
import { CACHE } from "@/util/constants/cacheConstants";
import { makeRequest } from "@/util/actions/makeRequest";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { FilterDTO } from "@/objects/interface/filter.interface";
import { Filter } from "@/objects/class/filter/Filter";
import { auth } from "@/auth";
import FilterModal from "@/ui/components/modals/filter";
import FilterBar from "@/ui/pages/search/filterBar";
import FooterComponent from "@/ui/pages/home/footer";
import Navbar from "@/ui/components/navbar";
import ClubGrid from "@/ui/components/grid/club";
import SearchDetailHeader from "@/ui/pages/search/header";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { ParamsProvider } from "@/contexts/ParamsProvider";

export default async function ClubSearchPage(props: any) {
    const session = await auth();

    const paramsHelper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );

    const { data, total, filters } = await makeRequest<ClubSearchResponse>(
        APIRoutePath.ClubSearch,
        {
            searchParams: paramsHelper.asUrlSearchParams(),
            session,
            next: {
                revalidate: CACHE.search,
                tags: [
                    "club-search-data",
                    session?.user?.id ? session?.user?.id.toString() : "",
                ],
            },
        },
    );

    const parsedFilters = filters.map(
        (dto: FilterDTO) =>
            new Filter(dto, paramsHelper.getParamValue(QueryProperty.Filters)),
    );

    return (
        <main className="min-h-screen w-full bg-ivory">
            <ParamsProvider value={paramsHelper.asUrlSearchParams()}>
                <FilterModal filters={filters} total={total} />
                <SearchDetailHeader
                    title={`Search clubs`}
                    subTitle={`${total} results`}
                />
                <FilterBar
                    variant={SearchVariant.AllClubs}
                    total={total}
                    filters={parsedFilters.length > 0}
                />
                <ClubGrid clubs={data} />
            </ParamsProvider>
        </main>
    );
}
