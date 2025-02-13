/* eslint-disable @typescript-eslint/no-explicit-any */
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { APIRoutePath, QueryProperty } from "@/objects/enum";
import { ClubSearchResponse } from "@/app/api/club/search/interface";
import { CACHE } from "@/util/constants/cacheConstants";
import { makeRequest } from "@/util/actions/makeRequest";
import { FilterDTO } from "@/objects/interface/filter.interface";
import { Filter } from "@/objects/class/filter/Filter";
import { auth } from "@/auth";
import FilterModal from "@/ui/components/modals/filter";
import FilterBar from "@/ui/pages/search/filterBar";
import ClubGrid from "@/ui/components/grid/club";
import SearchDetailHeader from "@/ui/pages/search/header";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { ParamsProvider } from "@/contexts/ParamsProvider";
import { getSearchedClubs } from "@/lib/data/club/search/getSearchedClubs";
import { unstable_cache } from "next/cache";
import { Session } from "next-auth";

export default async function ClubSearchPage(props: any) {
    const session = await auth();

    const paramsHelper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );

    const getCachedSearchPageData = (
        paramsHelper: SearchParamsHelper,
        currentSession: Session | null,
    ) =>
        unstable_cache(
            async () => {
                try {
                    return await getSearchedClubs(
                        paramsHelper.asParamsString(),
                    );
                } catch (error) {
                    console.error("Club serach page data fetch error:", error);
                    throw error;
                }
            },
            ["club-search-data", currentSession?.profile?.userId ?? ""],
            {
                revalidate: CACHE.search,
                tags: [
                    "club-search-data",
                    currentSession?.profile?.userId ?? "",
                ],
            },
        );

    const { data, total, filters } = await getCachedSearchPageData(
        paramsHelper,
        session,
    )();

    return (
        <main className="min-h-screen w-full bg-ivory">
            <ParamsProvider value={paramsHelper.asUrlSearchParams()}>
                <FilterModal filters={[]} total={total} />
                <SearchDetailHeader
                    title={`Search clubs`}
                    subTitle={`${total} results`}
                />
                <FilterBar
                    variant={SearchVariant.AllClubs}
                    total={total}
                    filters={filters.length > 0}
                />
                <ClubGrid clubs={data} />
            </ParamsProvider>
        </main>
    );
}
