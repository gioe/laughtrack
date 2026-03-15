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
import { toSearchParams } from "@/util/search/toSearchParams";
import { cookies } from "next/headers";

interface ComedianSearchPageProps {
    searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function ComedianSearchPage(
    props: ComedianSearchPageProps,
) {
    const [session, cookieStore, searchParams] = await Promise.all([
        auth(),
        cookies(),
        props.searchParams,
    ]);

    const theme =
        typeof searchParams.theme === "string" ? searchParams.theme : undefined;

    const requestData = {
        params: toSearchParams(searchParams),
        timezone: cookieStore.get("timezone")?.value || "UTC",
        userId: session?.profile?.userid,
        profileId: session?.profile?.id,
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
        <>
            <FilterModal filters={filters} total={total} />

            <SearchDetailHeader
                title="Search comedians"
                subTitle={`${total} results`}
                variant="comedian"
                theme={theme}
                tagline="Find comedians performing near you"
            />

            <FilterBar
                variant={SearchVariant.AllComedians}
                total={total}
                filters={filters.length}
            />

            <ComedianGrid
                comedians={data}
                className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6"
            />
        </>
    );
}
