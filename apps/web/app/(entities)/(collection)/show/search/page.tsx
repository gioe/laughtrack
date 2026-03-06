import { auth } from "@/auth";
import { CACHE } from "@/util/constants/cacheConstants";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { unstable_cache } from "next/cache";
import { getSearchedShows } from "@/lib/data/show/search/getSearchedShows";
import { ParameterizedRequestData } from "@/objects/interface";
import FilterBar from "@/ui/pages/search/filterBar";
import ShowTable from "@/ui/pages/search/table";
import FilterModal from "@/ui/components/modals/filter";
import { cookies } from "next/headers";

export default async function ShowSearchPage(props: any) {
    const [session, cookieStore, searchParams] = await Promise.all([
        auth(),
        cookies(),
        props.searchParams,
    ]);

    const requestData = {
        params: searchParams,
        timezone: cookieStore.get("timezone")?.value || "UTC",
        userId: session?.profile?.userid,
        profileId: session?.profile?.id,
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
            ["show-search-data", JSON.stringify(requestData)],
            {
                revalidate: CACHE.search,
                tags: ["show-search-data", JSON.stringify(requestData)],
            },
        );

    const { data, total, filters } =
        await getCachedSearchPageData(requestData)();
    return (
        <main className="min-h-screen w-full bg-coconut-cream">
            <FilterModal filters={filters} total={total} />
            <FilterBar
                variant={SearchVariant.AllShows}
                total={total}
                filters={filters.length}
            />
            <ShowTable shows={data} />
        </main>
    );
}
