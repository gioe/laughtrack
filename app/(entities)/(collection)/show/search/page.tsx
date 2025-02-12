import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { QueryProperty } from "@/objects/enum";
import { auth } from "@/auth";
import Navbar from "@/ui/components/navbar";
import FilterBar from "@/ui/pages/search/filterBar";
import ShowTable from "@/ui/pages/search/table";
import SearchDetailHeader from "@/ui/pages/search/header";
import FilterModal from "@/ui/components/modals/filter";
import { CACHE } from "@/util/constants/cacheConstants";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { ParamsProvider } from "@/contexts/ParamsProvider";
import { unstable_cache } from "next/cache";
import { getSearchedShows } from "@/lib/data/show/search/getSearchedShows";
import { Session } from "next-auth";

export default async function ShowSearchPage(props: any) {
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
                    return await getSearchedShows(paramsHelper);
                } catch (error) {
                    console.error("Show search page data fetch error:", error);
                    throw error;
                }
            },
            ["show-search-data", currentSession?.profile?.userId ?? ""],
            {
                revalidate: CACHE.search,
                tags: [
                    "show-search-data",
                    currentSession?.profile?.userId ?? "",
                ],
            },
        );

    const { data, total, filters } = await getCachedSearchPageData(
        paramsHelper,
        session,
    )();

    const zip = paramsHelper.getParamValue(QueryProperty.Zip);
    return (
        <main className="min-h-screen w-full bg-ivory">
            <Navbar currentUser={session?.profile} />
            <ParamsProvider value={paramsHelper.asUrlSearchParams()}>
                <FilterModal filters={filters} total={total} />
                <SearchDetailHeader
                    title={`Search for shows near ${zip}`}
                    subTitle={`${total} results`}
                />
                <FilterBar
                    variant={SearchVariant.AllShows}
                    total={total}
                    filters={filters.length > 0}
                />
                <div className="mx-10">
                    <ShowTable shows={data} />
                </div>
            </ParamsProvider>
        </main>
    );
}
