import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { CACHE } from "@/util/constants/cacheConstants";
import { auth } from "@/auth";
import ComedianDetailHeader from "@/ui/pages/entity/comedian/header";
import TableWithHeader from "@/ui/pages/entity/comedian/table";
import FilterBar from "@/ui/pages/search/filterBar";
import FilterModal from "@/ui/components/modals/filter";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { ParamsProvider } from "@/contexts/ParamsProvider";
import { unstable_cache } from "next/cache";
import { getComedianDetailPageData } from "@/lib/data/comedian/detail/getComedianDetailPageData";
import { Session } from "next-auth";

export default async function ComedianDetailsPage(props: any) {
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
                    return await getComedianDetailPageData(
                        paramsHelper.asParamsString(),
                    );
                } catch (error) {
                    console.error(
                        "Comedian detail page data fetch error:",
                        error,
                    );
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
                <FilterModal filters={[]} total={total} />
                <ComedianDetailHeader comedian={data} />
                <div className="max-w-7xl mx-auto p-6">
                    <TableWithHeader shows={shows} total={total}>
                        <FilterBar
                            variant={SearchVariant.ComedianDetail}
                            total={total}
                            filters={filters.length > 0}
                        />
                    </TableWithHeader>
                </div>
            </ParamsProvider>
        </main>
    );
}
