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

export default async function ComedianDetailsPage(props: any) {
    const session = await auth();

    const paramsHelper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const getCachedDetailPageData = (paramsHelper: SearchParamsHelper) =>
        unstable_cache(
            async () => {
                try {
                    return await getComedianDetailPageData(paramsHelper);
                } catch (error) {
                    console.error("Home page data fetch error:", error);
                    throw error;
                }
            },
            [
                "comedian-detail-data",
                session?.user?.id ? session?.user?.id.toString() : "",
            ],
            {
                revalidate: CACHE.detailPage,
                tags: [
                    "comedian-detail-data",
                    session?.user?.id ? session?.user?.id.toString() : "",
                ],
            },
        );

    const { data, shows, total, filters } =
        await getCachedDetailPageData(paramsHelper)();

    return (
        <main className="min-h-screen w-full bg-ivory">
            <ParamsProvider value={paramsHelper.asUrlSearchParams()}>
                <FilterModal filters={filters} total={total} />

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
