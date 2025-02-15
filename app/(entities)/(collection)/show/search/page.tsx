import { QueryProperty } from "@/objects/enum";
import { auth } from "@/auth";
import Navbar from "@/ui/components/navbar";
import FilterBar from "@/ui/pages/search/filterBar";
import ShowTable from "@/ui/pages/search/table";
import SearchDetailHeader from "@/ui/pages/search/header";
import FilterModal from "@/ui/components/modals/filter";
import { CACHE } from "@/util/constants/cacheConstants";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { unstable_cache } from "next/cache";
import { getSearchedShows } from "@/lib/data/show/search/getSearchedShows";
import { ParameterizedRequestData } from "@/objects/interface";

export default async function ShowSearchPage(props: any) {
    const session = await auth();

    const searchParams = await props.searchParams();

    const requestData = {
        params: searchParams,
        userId: session?.profile?.userId,
    };

    const getCachedSearchPageData = (requestData: ParameterizedRequestData) =>
        unstable_cache(
            async () => {
                try {
                    return await getSearchedShows(requestData);
                } catch (error) {
                    console.error("Show search page data fetch error:", error);
                    throw error;
                }
            },
            ["show-search-data", requestData.userId ?? "", requestData.params],
            {
                revalidate: CACHE.search,
                tags: [
                    "show-search-data",
                    requestData.userId ?? "",
                    `show-search-${requestData.params}`,
                ],
            },
        );

    const { data, total, filters } =
        await getCachedSearchPageData(requestData)();

    return (
        <main className="min-h-screen w-full bg-ivory">
            <Navbar currentUser={session?.profile} />
            <FilterModal filters={filters} total={total} />
            <SearchDetailHeader
                title={`Search for shows near ${searchParams.get(QueryProperty.Zip)}`}
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
        </main>
    );
}
