/* eslint-disable @typescript-eslint/no-explicit-any */
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { CACHE } from "@/util/constants/cacheConstants";
import { auth } from "@/auth";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { ParamsProvider } from "@/contexts/ParamsProvider";
import { getSearchedComedians } from "@/lib/data/comedian/search/getSearchedComedians";
import { Session } from "next-auth";
import { unstable_cache } from "next/cache";
import ComedianGrid from "@/ui/components/grid/comedian";
import SearchDetailHeader from "@/ui/pages/search/header";
import FilterModal from "@/ui/components/modals/filter";
import FilterBar from "@/ui/pages/search/filterBar";

export default async function ComedianSearchPage(props: any) {
    const session = await auth();

    const paramsHelper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );
    const getCachedSearchPageData = (
        paramsHelper: SearchParamsHelper,
        currentSession: Session | null,
    ) => {
        // Create a unique cache key based on the query parameters
        const queryParamsKey = paramsHelper.asParamsString();

        return unstable_cache(
            async () => {
                try {
                    return await getSearchedComedians(
                        queryParamsKey,
                        currentSession?.profile?.userId,
                    );
                } catch (error) {
                    console.error(
                        "Comedian search page data fetch error:",
                        error,
                    );
                    throw error;
                }
            },
            [
                "comedian-search-data",
                currentSession?.profile?.userId ?? "",
                queryParamsKey, // Add query params to cache key
            ],
            {
                revalidate: CACHE.search,
                tags: [
                    "comedian-search-data",
                    currentSession?.profile?.userId ?? "",
                    `comedian-search-${queryParamsKey}`, // Add query-specific tag
                ],
            },
        );
    };

    const { data, total, filters } = await getCachedSearchPageData(
        paramsHelper,
        session,
    )();

    return (
        <main className="min-h-screen w-full bg-ivory">
            <FilterModal filters={[]} total={total} />

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
        </main>
    );
}
