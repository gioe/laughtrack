/* eslint-disable @typescript-eslint/no-explicit-any */
import { CACHE } from "@/util/constants/cacheConstants";
import { auth } from "@/auth";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { getSearchedComedians } from "@/lib/data/comedian/search/getSearchedComedians";
import { unstable_cache } from "next/cache";
import ComedianGrid from "@/ui/components/grid/comedian";
import SearchDetailHeader from "@/ui/pages/search/header";
import FilterModal from "@/ui/components/modals/filter";
import FilterBar from "@/ui/pages/search/filterBar";
import { ParameterizedRequestData } from "@/objects/interface";

export default async function ComedianSearchPage(props: any) {
    const [session, searchParams] = await Promise.all([
        auth(),
        props.searchParams,
    ]);

    const requestData = {
        params: searchParams,
        userId: session?.profile?.userId,
    };

    const getCachedSearchPageData = (requestData: ParameterizedRequestData) => {
        return unstable_cache(
            async () => {
                try {
                    return await getSearchedComedians(requestData);
                } catch (error) {
                    console.error(
                        "Comedian search page data fetch error:",
                        error,
                    );
                    throw error;
                }
            },
            ["comedian-search-data", JSON.stringify(requestData)],
            {
                revalidate: CACHE.search,
                tags: ["comedian-search-data", JSON.stringify(requestData)],
            },
        );
    };

    const { data, total, filters } =
        await getCachedSearchPageData(requestData)();

    return (
        <main className="min-h-screen w-full bg-coconut-cream">
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
                className="grid grid-cols-2 gap-6 m:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
            />
        </main>
    );
}
