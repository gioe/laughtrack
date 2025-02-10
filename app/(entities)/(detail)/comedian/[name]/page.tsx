import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { APIRoutePath } from "@/objects/enum";
import { CACHE } from "@/util/constants/cacheConstants";
import { makeRequest } from "@/util/actions/makeRequest";
import { ComedianDetailResponse } from "@/app/api/comedian/[name]/interface";
import { auth } from "@/auth";
import ComedianDetailHeader from "@/ui/pages/entity/comedian/header";
import FooterComponent from "@/ui/pages/home/footer";
import TableWithHeader from "@/ui/pages/entity/comedian/table";
import FilterBar from "@/ui/pages/search/filterBar";
import FilterModal from "@/ui/components/modals/filter";
import Navbar from "@/ui/components/navbar";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { ParamsProvider } from "@/contexts/ParamsProvider";

export default async function ComedianDetailsPage(props: any) {
    const session = await auth();

    const paramsHelper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { data, shows, total, filters } =
        await makeRequest<ComedianDetailResponse>(
            APIRoutePath.Comedian + `/${paramsHelper.asSlug()}`,
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
            <Navbar currentUser={session?.user} />
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
            <FooterComponent />
        </main>
    );
}
