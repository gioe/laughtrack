/* eslint-disable @typescript-eslint/no-explicit-any */
import { CACHE } from "@/util/constants/cacheConstants";
import { auth } from "@/auth";
import FilterModal from "@/ui/components/modals/filter";
import FilterBar from "@/ui/pages/search/filterBar";
import ClubGrid from "@/ui/components/grid/club";
import SearchDetailHeader from "@/ui/pages/search/header";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { getSearchedClubs } from "@/lib/data/club/search/getSearchedClubs";
import { unstable_cache } from "next/cache";
import { ParameterizedRequestData } from "@/objects/interface";

export default async function ClubSearchPage(props: any) {
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
                    return await getSearchedClubs(requestData);
                } catch (error) {
                    console.error("Club serach page data fetch error:", error);
                    throw error;
                }
            },
            ["club-search-data", requestData.userId ?? "", requestData.params],
            {
                revalidate: CACHE.search,
                tags: [
                    "club-search-data",
                    requestData.userId ?? "",
                    `club-search-${requestData.params}`,
                ],
            },
        );

    const { data, total, filters } =
        await getCachedSearchPageData(requestData)();

    return (
        <main className="min-h-screen w-full bg-ivory">
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
        </main>
    );
}
