import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { APIRoutePath } from "@/objects/enum";
import { CACHE } from "@/util/constants/cacheConstants";
import { makeRequest } from "@/util/actions/makeRequest";
import { DynamicRoute } from "@/objects/interface/identifable.interface";
import { ClubDetailResponse } from "@/app/api/club/[name]/interface";
import { auth } from "@/auth";
import Navbar from "@/ui/components/navbar";
import TableWithHeader from "@/ui/pages/entity/comedian/table";
import FooterComponent from "@/ui/pages/home/footer";
import ClubDetailHeader from "@/ui/pages/entity/club/header";
import FilterBar from "@/ui/pages/search/filterBar";
import FilterModal from "@/ui/components/modals/filter";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { ParamsProvider } from "@/contexts/ParamsProvider";

export default async function ClubDetailPage(props: {
    searchParams: Promise<URLSearchParams>;
    params: Promise<DynamicRoute> | undefined;
}) {
    const session = await auth();

    const paramsHelper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { data, shows, total, filters } =
        await makeRequest<ClubDetailResponse>(
            APIRoutePath.Club + `/${paramsHelper.asSlug()}`,
            {
                searchParams: paramsHelper.asUrlSearchParams(),
                session,
                next: {
                    revalidate: CACHE.detailPage,
                    tags: [
                        "comedian-detail-data",
                        session?.user?.id ? session?.user?.id.toString() : "",
                    ],
                },
            },
        );

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
