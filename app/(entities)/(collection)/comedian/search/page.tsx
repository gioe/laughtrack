/* eslint-disable @typescript-eslint/no-explicit-any */
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { CACHE } from "@/util/constants/cacheConstants";
import { auth } from "@/auth";
import ComedianGrid from "@/ui/components/grid/comedian";
import SearchDetailHeader from "@/ui/pages/search/header";
import FilterModal from "@/ui/components/modals/filter";
import FilterBar from "@/ui/pages/search/filterBar";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { ParamsProvider } from "@/contexts/ParamsProvider";
import { getSearchedComedians } from "@/lib/data/comedian/search/getSearchedComedians";
import { Session } from "next-auth";
import { unstable_cache } from "next/cache";

export default async function ComedianSearchPage(props: any) {
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
                    return await getSearchedComedians(paramsHelper);
                } catch (error) {
                    console.error(
                        "Comedian serach page data fetch error:",
                        error,
                    );
                    throw error;
                }
            },
            ["comedian-search-data", currentSession?.profile?.userId ?? ""],
            {
                revalidate: CACHE.search,
                tags: [
                    "comedian-search-data",
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
        </main>
    );
}
