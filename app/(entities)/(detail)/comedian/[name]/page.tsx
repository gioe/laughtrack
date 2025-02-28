import { CACHE } from "@/util/constants/cacheConstants";
import { auth } from "@/auth";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { unstable_cache } from "next/cache";
import { getComedianDetailPageData } from "@/lib/data/comedian/detail/getComedianDetailPageData";
import { ParameterizedRequestData } from "@/objects/interface";
import ComedianDetailHeader from "@/ui/pages/entity/comedian/header";
import TableWithHeader from "@/ui/pages/entity/comedian/table";
import FilterBar from "@/ui/pages/search/filterBar";
import FilterModal from "@/ui/components/modals/filter";
import { cookies } from "next/headers";

export default async function ComedianDetailsPage(props: {
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
                    return await getComedianDetailPageData(requestData);
                } catch (error) {
                    console.error(
                        "Comedian detail page data fetch error:",
                        error,
                    );
                    throw error;
                }
            },
            ["comedian-detail-data", JSON.stringify(requestData)],
            {
                revalidate: CACHE.detailPage,
                tags: ["comedian-detail-data", JSON.stringify(requestData)],
            },
        );

    const { data, shows, total, filters } =
        await getCachedDetailPageData(requestData)();

    return (
        <main className="min-h-screen w-full bg-coconut-cream">
            <FilterModal filters={filters} total={total} />
            <ComedianDetailHeader comedian={data} />
            <div className="max-w-7xl mx-auto p-6">
                <TableWithHeader
                    shows={shows}
                    total={total}
                    errorMessage="No results. Clearly this comic doesn't work enough."
                >
                    <FilterBar
                        variant={SearchVariant.ComedianDetail}
                        total={total}
                        filters={filters.length > 0}
                    />
                </TableWithHeader>
            </div>
        </main>
    );
}
