import { CACHE } from "@/util/constants/cacheConstants";
import { auth } from "@/auth";
import TableWithHeader from "@/ui/pages/entity/comedian/table";
import ClubDetailHeader from "@/ui/pages/entity/club/header";
import FilterBar from "@/ui/pages/search/filterBar";
import FilterModal from "@/ui/components/modals/filter";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { getClubDetailPageData } from "@/lib/data/club/detail/getClubDetailPageData";
import { unstable_cache } from "next/cache";
import { ParameterizedRequestData } from "@/objects/interface";
import { cookies } from "next/headers";
import ShowTable from "@/ui/pages/search/table";

export default async function ClubDetailPage(props: {
    searchParams: Promise<any>;
    params: Promise<{ name: string }> | undefined;
}) {
    const [session, cookieStore, searchParams, slug] = await Promise.all([
        auth(),
        cookies(),
        props.searchParams,
        props.params,
    ]);

    const requestData = {
        params: searchParams,
        timezone: cookieStore.get("timezone")?.value || "UTC",
        userId: session?.profile?.userId,
        profileId: session?.profile?.id,
        slug: slug?.name,
    };

    const getCachedDetailPageData = (requestData: ParameterizedRequestData) =>
        unstable_cache(
            async () => {
                try {
                    return await getClubDetailPageData(requestData);
                } catch (error) {
                    console.error("Club detail page data fetch error:", error);
                    throw error;
                }
            },
            ["club-detail-data", JSON.stringify(requestData)],
            {
                revalidate: CACHE.detailPage,
                tags: ["club-detail-data", JSON.stringify(requestData)],
            },
        );

    const { data, shows, total, filters } =
        await getCachedDetailPageData(requestData)();
    return (
        <main className="min-h-screen w-full bg-coconut-cream">
            <FilterModal filters={filters} total={total} />
            <ClubDetailHeader club={data} />
            <FilterBar
                variant={SearchVariant.ClubDetail}
                total={total}
                filters={filters.length > 0}
            />
            <ShowTable shows={shows} />
        </main>
    );
}
