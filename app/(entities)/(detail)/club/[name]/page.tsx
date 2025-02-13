import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { CACHE } from "@/util/constants/cacheConstants";
import { DynamicRoute } from "@/objects/interface/identifable.interface";
import { auth } from "@/auth";
import TableWithHeader from "@/ui/pages/entity/comedian/table";
import ClubDetailHeader from "@/ui/pages/entity/club/header";
import FilterBar from "@/ui/pages/search/filterBar";
import FilterModal from "@/ui/components/modals/filter";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { ParamsProvider } from "@/contexts/ParamsProvider";
import { getClubDetailPageData } from "@/lib/data/club/detail/getClubDetailPageData";
import { unstable_cache } from "next/cache";
import { Session } from "next-auth";

export default async function ClubDetailPage(props: {
    searchParams: Promise<URLSearchParams>;
    params: Promise<DynamicRoute> | undefined;
}) {
    const session = await auth();

    const paramsHelper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const getCachedDetailPageData = (
        paramsHelper: SearchParamsHelper,
        currentSession: Session | null,
    ) =>
        unstable_cache(
            async () => {
                try {
                    return await getClubDetailPageData(
                        paramsHelper.asParamsString(),
                    );
                } catch (error) {
                    console.error("Club detail page data fetch error:", error);
                    throw error;
                }
            },
            ["comedian-detail-data", currentSession?.profile?.userId ?? ""],
            {
                revalidate: CACHE.detailPage,
                tags: [
                    "comedian-detail-data",
                    currentSession?.profile?.userId ?? "",
                ],
            },
        );

    const { data, shows, total, filters } = await getCachedDetailPageData(
        paramsHelper,
        session,
    )();

    return (
        <main className="min-h-screen w-full bg-ivory">
            <ParamsProvider value={paramsHelper.asUrlSearchParams()}>
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
            </ParamsProvider>
        </main>
    );
}
