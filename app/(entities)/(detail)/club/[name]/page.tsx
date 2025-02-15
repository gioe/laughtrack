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

export default async function ClubDetailPage(props: {
    searchParams: Promise<URLSearchParams>;
    params: Promise<{ name: string }> | undefined;
}) {
    const session = await auth();
    const searchParams = await props.searchParams;
    const slug = await props.params;

    const requestData = {
        params: searchParams.toString(),
        userId: session?.profile?.userId,
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
            ["club-detail-data", requestData.userId ?? "", requestData.params],
            {
                revalidate: CACHE.detailPage,
                tags: [
                    "club-detail-data",
                    requestData.userId ?? "",
                    `club-detail-${requestData.params}`,
                ],
            },
        );

    const { data, shows, total, filters } =
        await getCachedDetailPageData(requestData)();

    return (
        <main className="min-h-screen w-full bg-ivory">
            <FilterModal filters={filters} total={total} />
            <ClubDetailHeader club={data} />
            <div className="max-w-7xl mx-auto p-6 flex flex-row">
                <TableWithHeader shows={shows} total={total}>
                    <FilterBar
                        variant={SearchVariant.ClubDetail}
                        total={total}
                        filters={filters.length > 0}
                    />
                </TableWithHeader>
            </div>
        </main>
    );
}
