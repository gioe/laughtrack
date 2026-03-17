import { auth } from "@/auth";
import { CACHE } from "@/util/constants/cacheConstants";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { unstable_cache } from "next/cache";
import { getSearchedShows } from "@/lib/data/show/search/getSearchedShows";
import { ParameterizedRequestData } from "@/objects/interface";
import { toSearchParams } from "@/util/search/toSearchParams";
import FilterBar from "@/ui/pages/search/filterBar";
import ShowSearchClient from "@/ui/pages/search/show/ShowSearchClient";
import FilterModal from "@/ui/components/modals/filter";
import { cookies } from "next/headers";
import { Suspense } from "react";

export default async function ShowSearchPage(props: any) {
    const [session, cookieStore, searchParams] = await Promise.all([
        auth(),
        cookies(),
        props.searchParams,
    ]);

    const requestData = {
        params: toSearchParams(searchParams),
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
        <>
            <FilterModal filters={filters} total={total} />
            <FilterBar
                variant={SearchVariant.AllShows}
                total={total}
                filters={filters.length}
            />
            <Suspense>
                <ShowSearchClient
                    initialData={data}
                    initialTotal={total}
                    initialFilters={filters}
                />
            </Suspense>
        </>
    );
}
